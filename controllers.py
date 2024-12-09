import logging
from collections import UserDict
from django.db.models import Q
from django.conf import settings
import datetime
from django.utils.module_loading import import_string
from datetime import timedelta, datetime

from rest_framework.exceptions import ValidationError
from rest_framework import status

from .models import (
    BillingInformation, FeeLogs, FeeProfile, Installment,
    UserSubscription, Transaction, VerifiedFundingsource, WebhookDetail,
    SubscriptionPlan, PlanCost, PaymentDescriptor, Client, PackageConfig)

from .payment_providers import dwolla_provider, stripe_provider, plaid_provider

logger = logging.getLogger(__file__)


class UserSubscriptionController():
    """
    This class holds actions required to interact with UserSubscription model
    """

    def __init__(self, provider, user_sub_id, user):
        self.provider = provider
        self.user = user
        self.user_subscription = self.__get_object(user_sub_id)

    def __get_object(self, user_sub_id):
        try:
            user_sub_obj = UserSubscription.objects.filter(provider=self.provider).get(id=user_sub_id)
            if user_sub_obj.user != self.user and user_sub_obj.subscriber != self.user:
                raise Exception('you dont have access to this obj')
            return user_sub_obj
        except Exception as e:
            logger.error("Error in UserSubscriptionController.__get_object: " + str(e))
            raise UserSubscription.DoesNotExist

    def save_object(self):
        self.user_subscription.save()

    def are_both_funding_sources_added(self):
        """checks if both user and subscriber add thir funding source"""
        if self.user_subscription.senderFundingsource and self.user_subscription.receiverFundingsource:
            return True
        return False

    @classmethod
    def cancel(cls, provider, user_subscription_id, account_id):
        """cancels a UserSubscription"""
        if provider == 'stripe':
            resp = stripe_provider.subscription().cancel(
                user_subscription_id, account_id
            )
            return resp
        return None

    @classmethod
    def cancel_scheduled_subscription(cls, provider, user_subscription_id, account_id):
        """cancels a UserSubscription"""
        if provider == 'stripe':
            resp = stripe_provider.SubscriptionSchedule.cancel_schedule(
                user_subscription_id, account_id
            )
            return resp
        return None

    def activate(self):
        """activates a UserSubscription"""
        self.user_subscription.active = True
        self.save_object()

    def update_sender_funding_source(self, funding_source):
        self.user_subscription.senderFundingsource = funding_source
        self.save_object()

    def update_receiver_funding_source(self, funding_source):
        self.user_subscription.receiverFundingsource = funding_source
        self.save_object()

    def update_billing_start_date(self, datetime_obj):
        self.user_subscription.date_billing_start = datetime_obj
        self.save_object()

    def update_billing_end_date(self, datetime_obj):
        self.user_subscription.date_billing_end = datetime_obj
        self.save_object()

    def update_billing_last_date(self, datetime_obj):
        self.user_subscription.date_billing_last = datetime_obj
        self.save_object()

    def update_billing_next_date(self, datetime_obj):
        self.user_subscription.date_billing_next = datetime_obj
        self.save_object()

    def update_plan_cost(self, plan_cost_object):
        self.user_subscription.subscription = plan_cost_object
        self.save_object()

    def list_installments(self):
        """return list of all installments of UserSubscription obj"""
        return self.user_subscription.subscription_installment.all()

    def list_transactions(self):
        """reutrns a list of all transactions of UserSubscription obj"""
        return self.user_subscription.transaction_set.all()

    def get_object(self):
        return self.user_subscription

    def calculate_payable_balance(self):
        """returns remaining balance that should user pay"""
        installments = self.user_subscription.subscription_installment.filter(status='empty').count()
        cost = self.user_subscription.subscription.cost
        return int(installments) * float(cost)

    def has_previous_transaction(self):
        """checks if therse is a pending transaction for this UserSubscription obj"""
        return Transaction.objects.filter(
            Q(user_subscription=self.user_subscription),
            Q(source_user=self.user_subscription.senderFundingsource),
            Q(type_of_payment='pay')).exclude(status='failed').exists()

        # (Q(installment__id=self.failed_transfer.installment.id)
        # &(Q(status='pending')|Q(status='processed')),
        # (Q(type_of_payment='payback') | Q(type_of_payment='repay_failed_payback'))).exists()

    def check_for_installments_existence(self):
        return Installment.objects.filter(subscription=self.user_subscription).exists()

    def create_installments(self):
        terms = int(self.user_subscription.term)
        for i in range(terms):
            Installment.objects.create(subscription=self.user_subscription)

    @classmethod
    def get_user_subscription_by_provider_id(cls, id):
        try:
            user_subscription = UserSubscription.objects.get(provider_usub_id=id)
        except:
            user_subscription = None
        return user_subscription

    @classmethod
    def list_user_subscriptions_as_owner(cls, user):
        """returns a list of current users UserSubscriptions(as owner of user sub)"""
        return UserSubscription.objects.filter(user=user)

    @classmethod
    def list_user_subscriptions_as_subscriber(cls, user):
        """returns a list of current users UserSubscriptions(as subscriber of user sub)"""
        return UserSubscription.objects.filter(subscriber=user)

    @classmethod
    def list_all_user_subscriptions(cls, user):
        """returns a list of current users UserSubscriptions(all of user sub obj)"""
        queryset1 = cls.list_user_subscriptions_as_owner(user)
        queryset2 = cls.list_user_subscriptions_as_subscriber(user)

        return queryset1 | queryset2

    @classmethod
    def list_installments_user_sub_queryset(cls, all_user_sub):
        """return list of all installment of a UserSubscription queryset"""
        list_installment = Installment.objects.none()
        for sub in all_user_sub:
            sub_installment = sub.subscription_installment.all()
            list_installment = list_installment | sub_installment
        return list_installment

    @classmethod
    def create(cls, *args, **kwargs):
        """creates a UserSubscription obj"""
        provider = PackageConfigController.get_provider()
        try:
            subscriber_user = kwargs.get('subscriber')
            try:
                sub_client = Client.objects.get(
                    user=subscriber_user, client_type='no_account')
            except:
                sub_client = Client.objects.get(
                    customer=subscriber_user, client_type='no_account')

            subscriber_billing = CustomerController().get_default_billing(
                client=sub_client
            )
            customer_id = subscriber_billing.customer_id
        except Exception as e:
            print('1.subscriber_billing not found')

        try:
            receiver_user = kwargs.get('user')
            rec_client = Client.objects.get(
                user=receiver_user, client_type='has_account', business=sub_client.business)
            receiver_user_billing = CustomerController().get_default_billing(
                client=rec_client
            )
            receiver_user_id = receiver_user_billing.account_id
        except Exception as e:
            print('2.receiver_user_billing not found')

        try:
            product_id = kwargs.get('subscription').provider_product_id
        except:
            print('3. price id not provided')

        subscription_object = UserSubscription(
            user=receiver_user_billing,
            subscriber=subscriber_billing,
            senderFundingsource=kwargs.get('senderFundingsource', None),
            receiverFundingsource=kwargs.get('receiverFundingsource', None),
            subscription=kwargs.get('subscription'),
            date_billing_start=kwargs.get('date_billing_start', None),
            date_billing_end=kwargs.get('date_billing_end', None),
            date_billing_last=kwargs.get('date_billing_last', None),
            date_billing_next=kwargs.get('date_billing_next', None),
            cancelled=kwargs.get('cancelled', False),
            active=kwargs.get('activate', False)
        )

        if provider == 'stripe':
            price_id = stripe_provider.subscription.get_price_id(
                product_id, receiver_user_id)
            resp = stripe_provider.subscription.create_user_subscription(
                customer_id=customer_id,
                price_id=price_id,
                connected_account=receiver_user_id,
                date_billing_end=kwargs.get('date_billing_end', None),
                application_fee_percent=kwargs.get('application_fee_percent', 0),
                billing_cycle_anchor=kwargs.get('billing_cycle_anchor', None),
                description=kwargs.get('description', None)
            )
            subscription_object.provider_usub_id = resp['id']
            try:
                subscription_object.client_secret = resp["latest_invoice"]["payment_intent"]["client_secret"]
            except:
                subscription_object.client_secret = None
        subscription_object.save()

        # create installment objects
        plan_cost = subscription_object.subscription
        for i in range(plan_cost.recurrence_period):
            Installment.objects.create(
                due_date=datetime.now(),
                subscription=subscription_object
            )

        return subscription_object

    @classmethod
    def create_subscription(cls, *args, **kwargs):
        errors = []
        provider = PackageConfigController.get_provider()
        # Get the client
        try:
            client = Client.objects.get(
                business=kwargs['business'], client_type='has_account')
        except Exception as e:
            print('clinet that has account not found')

        # Get billing info of the client
        try:
            billing_info_obj = BillingInformation.objects.get(
                client=client, provider=provider)

            kwargs['stripe_acc_id'] = billing_info_obj.account_id
        except Exception as e:
            print('clinet that has account not found')

        if provider == 'stripe':
            product_resp = stripe_provider.Product.create_product(**kwargs)

        subscirption_obj = SubscriptionPlan(
            plan_name=kwargs.get('plan_name')
        )
        subscirption_obj.save()

        # here save the price id also
        plan_cost_obj = PlanCost.objects.create(
            plan=subscirption_obj,
            recurrence_period=kwargs.get('recurrence_period'),
            recurrence_unit=kwargs.get('recurrence_unit'),
            cost=kwargs.get('plan_cost'),
            provider_product_id=product_resp['id']
        )
        return plan_cost_obj

    @classmethod
    def update_subscription(cls, *args, **kwargs):
        if getattr(settings, "PAYMENT_PROVIDER") == 'stripe':
            try:
                if 'price' in kwargs:
                    price = kwargs.pop('price')
                    recurring = kwargs.pop('recurring')
                    interval_count = kwargs.pop('interval_count')
                    currency = kwargs.pop('currency')
                    price_resp = stripe_provider.Product.update_product_price(
                        kwargs['product_id'],
                        price,
                        recurring,
                        interval_count,
                        currency
                    )
                product_resp = stripe_provider.Product.update(**kwargs)
                return product_resp
            except Exception as e:
                logger.error(f"UserSubscriptionController.update_subscription \ stripe_call error: {str(e)}")
        try:
            plan_cost_obj = PlanCost.objects.get(id=kwargs['product_id'])
            plan_cost_obj.recurrence_period = interval_count
            plan_cost_obj.recurrence_unit = recurring
            plan_cost_obj.cost = price
            if kwargs['name']:
                plan_obj = plan_cost_obj.plan
                plan_obj.plan_name = kwargs['name']
                plan_obj.save()
            plan_cost_obj.save()
        except Exception as e:
            logger.error(f"UserSubscriptionController.update_subscription \ db update error: {str(e)}")

    @classmethod
    def list_subscription_transactions(cls, user_subscription_id):
        try:
            user_sub_obj = UserSubscription.objects.get(id=user_subscription_id)
        except:
            raise Exception("UserSubscription not found.")
        return Transaction.objects.filter(user_subscription=user_sub_obj)

    @classmethod
    def create_stripe_product(cls, stripe_account, **kwargs):
        resp = stripe_provider.Product.create()
        return resp

    @classmethod
    def cancel_user_subscription(cls, provider, subscription_id, **kwargs):
        if provider == 'stripe':
            resp = stripe_provider.subscription.cancel()
        return resp

    @classmethod
    def retreive_user_subscription(cls, provider, subscription_id, stripe_account):
        if provider == 'stripe':
            resp = stripe_provider.subscription.retrieve(subscription_id, stripe_account)
        else:
            resp = None
        return resp

    @classmethod
    def retreive_scheduled_user_subscription(cls, provider, schedule_id, stripe_account):
        if provider == 'stripe':
            resp = stripe_provider.SubscriptionSchedule.retrieve(
                schedule_id, stripe_account)
        else:
            resp = None
        return resp

    @classmethod
    def modify_subscription_default_payment_method(
            cls, provider, subscription_id, default_payment_method, account_id):
        if provider == 'stripe':
            resp = stripe_provider.subscription.update_subscription_default_payment_method(
                subscription_id, default_payment_method, account_id
            )
            return resp

    @classmethod
    def modify_subscription_schedule_default_payment_method(
            cls, provider, schedule_id, default_payment_method, account_id):
        if provider == 'stripe':
            resp = stripe_provider.SubscriptionSchedule.update_schedule_default_payment_method(
                schedule_id, default_payment_method, account_id
            )
            return resp


class BaseInstallmentClass:
    """Base class for Installment model"""

    def get_object(self, installment_id):
        pass

    @classmethod
    def create(cls, *args, **kwargs):
        pass

    def update_status(self, status, status_change_date):
        pass

    def increase_retries(self):
        pass

    def set_user_subscription(self, user_sub_id):
        pass

    def increase_notifications_sent_times(self):
        pass

    def update_notifications_date(self):
        pass


class InstallmentController(BaseInstallmentClass):
    """This class holds actions required to interact with Installment model"""

    def __init__(self, installment_id):
        self.installment_object = self.get_object(installment_id)

    def get_object(self, installment_id):
        try:
            return Installment.objects.get(id=installment_id)
        except:
            raise Installment.DoesNotExist

    def save_object(self):
        self.installment_object.save()

    def update_status(self, status, status_change_date):
        """updates status and status_change_date of installment"""
        self.installment_object.status = status
        self.installment_object.status_change_date = status_change_date
        self.save_object()

    def increase_retries(self):
        """increase number of payment retries for a installment"""
        self.installment_object.retries += 1
        self.save_object()

    def set_user_subscription(self, user_sub_id):
        """sets user subscription for installment"""
        try:
            user_sub_obj = UserSubscription.objects.get(id=user_sub_id)
        except:
            raise UserSubscription.DoesNotExist
        self.installment_object.subscription = user_sub_obj
        self.save_object()

    def increase_notifications_sent_times(self):
        """increase number of how many times notification is sent for this installment"""
        self.installment_object.notifications_sent += 1
        self.save_object()

    def update_notifications_date(self, notification_sent_date):
        """updates last time a notification sent for this installment"""
        try:
            self.installment_object.notifications_sent_date = notification_sent_date
            self.save_object()
        except:
            raise ValidationError('Not valid data provided.')

    @classmethod
    def create(cls, *args, **kwargs):
        """
        creates an installment obj
        """
        installment_obj = Installment.objects.create(
            status=kwargs.get('status', None),
            status_change_date=kwargs.get('status_change_date', None),
            retries=kwargs.get('retries', 0),
            notifications_sent=kwargs.get('notifications_sent', 0),
            notifications_sent_date=kwargs.get('notifications_sent_date', None),
            subscription=kwargs.get('subscription', None)),
        return installment_obj

    @classmethod
    def user_subscription_installments(cls, user_subscription):
        return Installment.objects.filter(subscription=user_subscription).order_by('id')

    @classmethod
    def create_subscription_installments(cls, user_subscription, interval, interval_count):
        if interval not in ['day', 'month', 'year']:
            raise ValueError("Invalid interval. Choose from 'day', 'month', or 'year'.")

        due_date = datetime.now()
        time_delta = None

        if interval == 'day':
            time_delta = timedelta(days=1)
        elif interval == 'month':
            time_delta = timedelta(days=30)
        elif interval == 'year':
            time_delta = timedelta(days=365)

        for _ in range(interval_count):
            Installment.objects.create(
                due_date=due_date,
                subscription=user_subscription
            )
            due_date += time_delta


class FeesController():
    """This class holds actions required to interact with FeeProfile and Feelogs models"""

    def get_fee_by_name(self, names_list):
        """returns a list of FeeProfile objs based on its name"""
        try:
            fees_list = []
            for name in names_list:
                fee = FeeProfile.objects.filter(enabled=True). \
                    order_by('-updated').get(fee_type=name)
                fees_list.append(fee.fee)
            return fees_list
        except:
            raise ValidationError("No record found for loan_setup_fee")

    def save_fee_logs_by_transfer_id(self, provider, transfer_id):
        """get list of fees are taken from transaction"""
        fee_info = TransferController(provider).get_fee_of_transaction(transfer_id)
        total_fees = int(fee_info['total'])
        if total_fees != 0:
            for transaction in fee_info['transactions']:
                # Do the saving.
                link = transaction['_links']['self']['href']
                source = transaction['_links']['source']['href']
                status = transaction['status']
                amount = transaction['amount']['value']
                created_from_transfer = transaction['_links']['created-from-transfer']['href']
                transaction_object = TransferController.get_transfer_by_url(created_from_transfer)
                customer_obj = BillingInformation.objects.get(customer_url=source)
                FeeLogs.objects.create(
                    amount=amount,
                    status=status,
                    transfer_url=link,
                    transaction=transaction_object,
                    customer=customer_obj
                )

    def add_to_fees(self, provider, fees, customer_id, amount):
        """creates fee obj to add to a transaction"""
        if provider in ['dwolla', "dwolla+plaid"]:
            fees = dwolla_provider.add_to_fees(fees, customer_id, amount)

        return fees

    def update_fee_logs_status_by_transfer_id(self, provider, transfer_id):
        """updates feelogs status"""
        fee_info = TransferController().get_fee_of_transaction(provider, transfer_id)
        total_fees = int(fee_info['total'])
        if total_fees != 0:
            for transaction in fee_info['transactions']:
                fee_transfer_url = transaction['_links']['self']['href']
                try:
                    fee_log = FeeLogs.objects.get(transfer_url=fee_transfer_url)
                    fee_log.status = transaction['status']
                    fee_log.save()
                except:
                    pass

    def create_fee_profile(self, **kwargs):
        """create FeeProfile obj"""
        fee_obj = FeeProfile.objects.create(
            service=kwargs.get('service'),
            fee=kwargs.get('fee'),
            description=kwargs.get('description'),
            enabled=kwargs.get('enabled'),
            fee_type=kwargs.get('fee_type'),
        )
        return fee_obj

    def all_fee_profile_list(self):
        """return all FeeProfiles"""
        return FeeProfile.objects.all()


class GetPaymentInitiationTokenContorller:
    """returns the Payment Provider token that is needed in frontend to integrate with backend"""

    def __init__(self):
        pass

    def get_token(self, provider, customer_id=None):
        # stripe doesn't have customer_id
        try:
            if provider == 'dwolla':
                token = dwolla_provider.iav_token(customer_id)
            elif provider == 'stripe':
                token = None
                # stripe_resp= stripe_provider.connection_token()
                # token= stripe_resp['secret']
            return token
        except Exception as e:
            logger.error(str(e))
            return 'error'


class ClientController:
    @classmethod
    def get_user_client(self, user):
        try:
            client = Client.objects.get(user=user)
        except Exception as e:
            raise Exception({"error": f"error in getting the user client: {str(e)}"})
        return client

    @classmethod
    def get_user_business_client(self, user, business):
        try:
            client = Client.objects.get(user=user, business=business)
        except Exception as e:

            raise Exception({"error": f"error in getting the user client: {str(e)}"})
        return client

    @classmethod
    def get_client(self, client_id):
        try:
            business_model = import_string(settings.BUSINESS_MODEL)
            business_obj = business_model.objects.get(id=client_id)
            return business_obj
        except Exception as e:

            raise ValidationError({"error": "business with client_id not found"})

    @classmethod
    def get_customer(self, customer_id):
        customer_model = import_string(settings.CUSTOMER_MODEL)
        customer_obj = customer_model.objects.get(id=customer_id)
        return customer_obj

    @classmethod
    def get_client_by_customer(self, customer_id):
        # customer_model = import_string(settings.CUSTOMER_MODEL)
        # customer_obj = customer_model.objects.get(id=customer_id)
        client = Client.objects.get(customer=customer_id)
        return client

    @classmethod
    def get_or_create_client(self, is_admin_user, data, user=None):
        if is_admin_user:
            try:
                client_name = data.pop('client_name')
                client_id = data.pop('client_id')
                business_obj = self.get_client(client_id)
            except Exception as e:

                raise ValidationError(
                    {"error": "client_name and client_id should be provided for the \
                    first time you want to create billing for business."})
            clinet_obj, created = Client.objects.get_or_create(
                user=user, client_type='has_account', name=client_name,
                business=business_obj
            )
            return clinet_obj

        else:
            client_name = data['client_name']
            business = data['business']
            customer = data['customer']
            clinet_obj, created = Client.objects.get_or_create(
                user=user, client_type='no_account', name=client_name,
                business=business, customer=customer
            )
            return clinet_obj

    @classmethod
    def get_or_create_client2(self, is_admin_user, data, user=None):
        if is_admin_user:
            try:
                # client_name = data.pop('client_name')
                client_id = data.pop('client_id')
                business_obj = self.get_client(client_id)
            except Exception as e:

                raise ValidationError(
                    {"error": "client_name and client_id should be provided for the \
                    first time you want to create billing for business."})
            clinet_obj, created = Client.objects.get_or_create(
                user=user, client_type='has_account', business=business_obj
            )
            return clinet_obj

        else:
            business = data['business']
            customer = data['customer']
            clinet_obj, created = Client.objects.get_or_create(
                user=user, client_type='no_account', business=business, customer=customer
            )
            return clinet_obj

    @classmethod
    def add_customer_to_client(self, user):
        pass

    @classmethod
    def add_new_billing(self, user):
        pass

    @classmethod
    def add_customer_to_client(self, user):
        pass

    @classmethod
    def get_customer_master_account(self, user):
        client = self.get_user_client(user)
        try:
            master_account = BillingInformation.objects.get(
                client__business=client.business,
                client__client_type='has_account',
                provider='stripe'
            ).account_id
        except Exception as e:

            raise ValidationError({"error": f"getting master account {str(e)}"})
        return master_account

    @classmethod
    def get_customer_master_account_by_client(self, client):
        # client = self.get_user_client(user)
        try:
            master_account = BillingInformation.objects.get(
                client__business=client.business,
                client__client_type='has_account',
                provider='stripe'
            ).account_id
        except Exception as e:

            raise ValidationError({"error": f"getting master account {str(e)}"})
        return master_account

    @classmethod
    def get_client_by_customer_obj(cls, customer_obj):
        try:
            client = Client.objects.get(customer=customer_obj)
        except Exception as e:
            logger.exception(f'**Payment Package** exception in '
                             f'get_client_by_customer_obj: {str(e)}')
            raise
        return client

    @classmethod
    def get_billing_by_client(cls, business, client_type):
        try:
            client = Client.objects.get(business=business, client_type=client_type)
        except Exception as e:
            print(e)
            raise ValidationError(
                {'payment_package_error':
                     ['1.office needs to complete the payment package onboarding']})
        try:
            billing = BillingInformation.objects.get(client=client)
        except Exception as e:
            raise ValidationError(
                {'payment_package_error':
                     ['2.office needs to complete the payment package onboarding']})
        return client, billing


class CustomerController:
    """
    This class holds actions required to interact with BillingInfromation models
    and make api call with Payment provider to create/update/get/delete customer
    """

    def __init__(self):
        self.provider = PackageConfigController.get_provider()

    def create_billing_information(self, **kwargs):
        """creates a billing information obj"""
        billing_obj = BillingInformation.objects.create(**kwargs)

        return billing_obj

    def update_billing_information_obj(self, billing_obj, **kwargs):
        """updates a billing information obj"""
        billing_obj.first_name = kwargs.get('first_name', billing_obj.first_name)
        billing_obj.last_name = kwargs.get('last_name', billing_obj.last_name)
        billing_obj.email = kwargs.get('email', billing_obj.email)
        billing_obj.phone = kwargs.get('phone', billing_obj.phone)
        billing_obj.address1 = kwargs.get('address1', billing_obj.address1)
        billing_obj.address2 = kwargs.get('address2', billing_obj.address2)
        billing_obj.city = kwargs.get('city', billing_obj.city)
        billing_obj.state = kwargs.get('state', billing_obj.state)
        billing_obj.postalCode = kwargs.get('postalCode', billing_obj.postalCode)
        billing_obj.billing_type = kwargs.get('billing_type', billing_obj.billing_type)

        billing_obj.save()

        return billing_obj

    def get_user_billing_information(
            self, billing_type=None, client=None, user=None):
        # provider = PackageConfigController.get_provider()
        try:
            query = BillingInformation.objects
            if user:
                query = query.filter(client__user=user)
            if client:
                query = query.filter(client=client)
                # query = query.filter(provider=provider)
            if billing_type:
                user_billing_info = query.get(provider=self.provider, billing_type=billing_type)
            else:
                user_billing_info = query.get(provider=self.provider)
            return user_billing_info

        except BillingInformation.DoesNotExist:
            return None
        except Exception as e:
            logger.exception(f'{str(e)}')

    def get_billing_obj_with_customer_id(self, provider, customer_id=None, account_id=None):
        """
        get BillingInformation obj based on customer_id or account_id
        account_id is just for stripe provider
        """
        try:
            if customer_id:
                user_billing_info = BillingInformation.objects.filter(provider=provider).get(customer_id=customer_id)
            elif account_id:
                user_billing_info = BillingInformation.objects.filter(provider=provider).get(account_id=account_id)
            return user_billing_info
        except BillingInformation.DoesNotExist:
            return None
        except Exception as e:
            logger.error('error in CustomerController.get_billing_obj_with_customer_id:')

    def create_customer(self, is_admin_user, **kwargs):
        """
        creates a billing information obj then calls to payment provider and creates a customer
        """
        if is_admin_user:
            statement_descriptor = kwargs.pop('statement_descriptor')
        billing_obj = self.create_billing_information(**kwargs)

        if self.provider == 'dwolla':
            try:
                dwolla_customer_instance = dwolla_provider.DwollaCustomer()
                customer_data = dwolla_customer_instance.create_customer(
                    first_name=billing_obj.first_name, last_name=billing_obj.last_name,
                    phone=billing_obj.phone, email=billing_obj.email,
                    # type=billing_obj.customerType,
                    address1=billing_obj.address1,
                    address2=billing_obj.address2, city=billing_obj.city, state=billing_obj.state,
                    postalCode=billing_obj.postalCode, dateOfBirth=billing_obj.dateOfBirth, ssn=billing_obj.ssn
                )
                customer_id = customer_data.split('/')[-1]
                account_id = None
                billing_obj.customer_id = customer_id
                billing_obj.save()
            except Exception as e:
                logger.exception(f'{str(e)}')
        elif self.provider == 'stripe':
            if is_admin_user:
                try:
                    account_data = stripe_provider.StripeAccount().create_customer(
                        billing_type=billing_obj.billing_type,
                        email=billing_obj.email,
                        country=billing_obj.country,
                        statement_descriptor=statement_descriptor
                    )
                    account_id = account_data['account']
                    billing_obj.account_id = account_id
                    # if kwargs['billing_type'] == 'custom':
                    #     billing_obj.billing_type = 'stripe_custom'
                    # else:
                    #     billing_obj.billing_type = 'stripe_express'
                    billing_obj.save()
                except Exception as e:
                    logger.info(f'something went wrong during stripe call, deletign billign object: {str(e)}')
                    billing_obj.delete()
                    logger.exception(f'error - stripe create customer: {str(e)}')
                    raise ValidationError({'stripe error': f'something went wrong during stripe call {str(e)}'})

            else:  # client == customer

                stripe_account = ClientController.get_customer_master_account_by_client(
                    kwargs['client'])
                try:
                    customer_data = stripe_provider.StripeCustomer().create_customer(
                        first_name=billing_obj.first_name, last_name=billing_obj.last_name,
                        phone=billing_obj.phone, email=billing_obj.email,
                        address1=billing_obj.address1, address2=billing_obj.address2,
                        city=billing_obj.city, state=billing_obj.state,
                        postalCode=billing_obj.postalCode, dateOfBirth=billing_obj.dateOfBirth,
                        country=billing_obj.country, stripe_account=stripe_account
                    )
                    customer_id = customer_data['customer']
                    billing_obj.customer_id = customer_id
                    billing_obj.save()
                except Exception as e:
                    logger.info(f'something went wrong during stripe call, deletign billign object: {str(e)}')
                    billing_obj.delete()
                    logger.exception(f'error - stripe create customer: {str(e)}')
                    raise ValidationError({'stripe error': f'something went wrong during stripe call: {str(e)}'})

        if not billing_obj.customer_id and not billing_obj.account_id:
            billing_obj.delete()

        return billing_obj

    def retrieve_customer(self, provider, billing_obj):
        """retrieves data of a customer"""
        if provider == 'dwolla':
            customer_instance = dwolla_provider.DwollaCustomer().retrieve_customer(billing_obj.customer_id)
        elif provider == 'stripe':
            account_instance = stripe_provider.StripeAccount().retrieve_customer(billing_obj.account_id)
            customer_instance = stripe_provider.StripeCustomer().retrieve_customer(billing_obj.customer_id)

    def retreive_account_info(provider, billing_information):
        if provider == 'dwolla':
            account = dwolla_provider.DwollaCustomer().retrieve_customer(billing_information.customer_id)
        elif provider == 'stripe':
            account = stripe_provider.StripeAccount().retrieve_customer(billing_information.account_id)
        return account

    def list_customers(self, provider, **kwargs):
        """get a list of all customers"""
        if provider == 'dwolla':
            customer_list = dwolla_provider.DwollaCustomer()
        elif provider == 'stripe':
            customer_list = stripe_provider.StripeCustomer()

        customer_list.list_customers()

    def update_customer(self, billing_obj, is_admin, **kwargs):
        """
        updates a billing information obj then makes api call to payment provider and updates customer
        """
        updated_billing_obj = self.update_billing_information_obj(billing_obj, **kwargs)

        if updated_billing_obj.provider == 'dwolla':
            dwolla_customer_instance = dwolla_provider.DwollaCustomer()
            customer_data = dwolla_customer_instance.update_customer(
                updated_billing_obj.customer_id, address2=updated_billing_obj.address2,
                address1=updated_billing_obj.address1,
                state=updated_billing_obj.state, city=updated_billing_obj.city,
                postalCode=updated_billing_obj.postalCode,
                email=updated_billing_obj.email, phone=updated_billing_obj.phone
            )

        elif updated_billing_obj.provider == 'stripe':
            if is_admin:
                if updated_billing_obj.billing_type == 'express':
                    raise ValidationError({"error": "for express account use stripe \
                                           dashboard to update your account."})
                else:
                    kwargs['email'] = updated_billing_obj.email
                    resp = stripe_provider.StripeAccount.update_customer(
                        updated_billing_obj.account_id, kwargs
                    )
            else:
                stripe_account = ClientController.get_customer_master_account_by_client(
                    billing_obj.client
                )
                customer_data = stripe_provider.StripeCustomer().modify_customer(
                    billing_obj.customer_id, stripe_account, **kwargs)

            # stripe_customer_instance= stripe_provider.StripeAccount()
            # customer_data= stripe_customer_instance.update_customer(
            #     customer_id= billing_obj.account_id,
            #     email= billing_obj.email,
            # )

            # stripe_customer_instance= stripe_provider.StripeCustomer()
            # try:
            #     customer_data= stripe_customer_instance.update_customer(
            #         customer_id= billing_obj.customer_id,
            #         first_name= billing_obj.first_name, last_name =billing_obj.last_name, phone= billing_obj.phone,
            #         email= billing_obj.email, address1= billing_obj.address1, address2= billing_obj.address2,
            #         city= billing_obj.city, state= billing_obj.state, postalCode= billing_obj.postalCode,
            #         dateOfBirth= billing_obj.dateOfBirth, country=billing_obj.country
            #     )

        if not customer_data.get('error', False):
            return updated_billing_obj
        return 'error'

    def delete_customer(self, provider, customer_id):
        """makes an api call and deletes a customer"""
        if provider == 'stripe':
            stripe_provider.StripeCustomer().delete_customer(customer_id)
        if provider == "dwolla":
            # dwolla doesn't support this option
            pass

    def get_account_link(self, provider, account_id):
        """
        This method works just for stripe provider
        it returns a onboarding link
        """
        if provider == 'stripe':
            try:
                onboarding_link = stripe_provider.StripeAccount().get_account_link(account_id)
                return onboarding_link
            except Exception as u:
                logger.error(f"error in CustomerController.get_account_link: {u}")

    def get_client_billing(self, client, provider=None):
        try:
            if provider:
                billing_obj = BillingInformation.objects.get(
                    client=client, provider=provider)
            else:
                billing_obj = BillingInformation.objects.get(client=client)
        except Exception as e:
            raise Exception({"error": f"error in getting the client's billing: {str(e)}"})
        return billing_obj

    def get_default_billing(self, client):
        return BillingInformation.objects.get(
            provider=self.provider, client=client, is_default=True)


class WebhookController:
    """
    This class holds actions required to interact with WebhookDetail models
    and make api call with Payment provider to create/update/get/delete webhook
    """

    def __init__(self, provider):
        self.provider = provider

    def create_webhook_obj(self, webhook_url, webhook_id):
        """creates a webhook detail obj"""
        webhook_obj = WebhookDetail.objects.create(provider=self.provider, webhook_url=webhook_url,
                                                   webhook_id=webhook_id)
        return webhook_obj

    def create_webhook(self):
        """
        make an api call to payment provider and creates a webhook
        then creates a webhook detail obj
        """
        if self.provider == 'dwolla':
            webhook_data = dwolla_provider.DwollaWebhook().create_webhook()
        elif self.provider == 'stripe':
            webhook_data = stripe_provider.StripeWebhook().create_webhook()

            webhook_url = webhook_data
            webhook_id = webhook_data

            self.create_webhook_obj(webhook_url, webhook_id)

    def retrieve_webhook(self, webhook_id):
        """
        makes an api call with payment provider and return a detail of webhook
        """
        if self.provider == 'dwolla':
            webhook_data = dwolla_provider.DwollaWebhook().retrieve_webhook(webhook_id)
        elif self.provider == 'stripe':
            webhook_data = stripe_provider.StripeWebhook().retrieve_webhook(webhook_id)

    def update_webhook(self, webhook_id, webhook_status):
        """make an api call and updates a webhook status"""
        if self.provider == 'dwolla':
            webhook_data = dwolla_provider.DwollaWebhook().update_webhook(webhook_id, webhook_status)
        elif self.provider == 'stripe':
            webhook_data = stripe_provider.StripeWebhook().update_webhook(webhook_id, webhook_status)

    def list_webhooks(self):
        """makef an api call and returns list of all webhook of this app"""
        if self.provider == 'dwolla':
            webhook_data = dwolla_provider.DwollaWebhook().list_webhooks()
        elif self.provider == 'stripe':
            webhook_data = stripe_provider.StripeWebhook().list_webhooks()

    def delete_webhook(self, webhook_id):
        """makes an api call and deletes webhook"""
        if self.provider == 'dwolla':
            webhook_data = dwolla_provider.DwollaWebhook().delete_webhook(webhook_id)
        elif self.provider == 'stripe':
            webhook_data = stripe_provider.StripeWebhook().delete_webhook(webhook_id)


class FundingSourceController:
    """
    This class holds actions required to interact with VerifiedFundingSource models
    and make api call with Payment provider to create/update/get/delete funding source
    """

    def __init__(self):
        pass

    def create_verified_funding_source(self, **kwargs):
        """create a VerifiedFundingSource obj"""
        funding_source, created = VerifiedFundingsource.objects.get_or_create(
            profile=kwargs.pop('customer'),
            funding_id=kwargs.pop('funding_id'),
            defaults={
                'pending_microdeposit': True,
                **kwargs
            }
        )

        return funding_source

    def create_card_funding_source(self, **kwargs):
        try:
            funding_source = VerifiedFundingsource.objects.create(
                profile=kwargs.pop('customer'),
                funding_id=kwargs.pop('funding_id'),
            )
        except Exception as e:
            raise ValidationError({"error": f"error in creating funding source {str(e)}"})

    def update_verified_funding_source(self, funding_obj, **kwargs):
        """updates a VerifiedFundingSource obj"""
        funding_obj.fundingsource_name = kwargs.get('fundingsource_name')
        funding_obj.type_of_source = kwargs.get('type_of_source', funding_obj.type_of_source)
        funding_obj.deleted = kwargs.get('deleted', funding_obj.deleted)
        funding_obj.pending_microdeposit = kwargs.get('pending_microdeposit', funding_obj.pending_microdeposit)
        funding_obj.save()

        return funding_obj

    def get_verified_funding_source(self, billing_obj, funding_source_id):
        """return a VerifiedFundingSource obj"""
        try:
            return VerifiedFundingsource.objects.filter(profile=billing_obj).get(id=funding_source_id)
        except:
            return None

    def list_verified_funding_source(self, billing_obj):
        """return list of all Funding Sources of this user"""
        return VerifiedFundingsource.objects.filter(profile=billing_obj)

    def create_funding_source(self, **kwargs):
        """
        gets provider bank token
        after that makes an api call to add funding source to the customer
        then creates a VerifiedFundingSource
        after that makes another api call to verify this funding source with microdeposit
        """
        customer_obj = kwargs['customer_profile']
        if kwargs['is_admin'] and kwargs['customer_profile'].provider == 'stripe':
            customer_id = customer_obj.account_id
        else:
            customer_id = customer_obj.customer_id

        if kwargs['provider'] == "dwolla":
            access_token = plaid_provider.exchange_access_token(
                kwargs['public_token'])
            get_token = plaid_provider.get_dwolla_token(
                access_token, kwargs['account_id'])
            if get_token == 'microdeposit':
                self.create_verified_funding_source(
                    profile=customer_obj,
                    fundingsource_name=kwargs['fundingsource_name'],
                    plaid_account_id=kwargs['account_id'],
                    plaid_access_token=access_token,
                    pending_microdeposit=True
                )
                return {'detail': ['The bank account you\'ve added is under \
                    review and will be verified within the next 24 to 48 hours.']}, \
                    status.HTTP_200_OK
            elif get_token == 'error':
                return {'detail': ['Can\'t get plaid response']}, \
                    status.HTTP_400_BAD_REQUEST

            dwolla_response = dwolla_provider.DwollaFundingSource(). \
                create_funding_source(**kwargs)

            if dwolla_response == 'error':
                return {'detail': ['Couldn\'t get dwolla response']}, \
                    status.HTTP_400_BAD_REQUEST

            fundingsource_id = dwolla_response['_links']['about']['href'].split('/')[-1]

            funding_source_data = self.retrieve_funding_source('dwolla', fundingsource_id)
            bank_name = funding_source_data['bankName']
            type_of_source = funding_source_data['type']

        elif kwargs['provider'] == "stripe":
            funding_source_data = stripe_provider.StripeFundingSource(). \
                create_funding_source(
                customerid=customer_id,
                external_account=kwargs['bank_acc'],
                default_for_currency=kwargs['default_for_currency']
            )
            funding_id = funding_source_data['id']
            bank_name = funding_source_data['bank_name']
            type_of_source = funding_source_data['account_type']

        funding_obj = self.create_verified_funding_source(
            customer=customer_obj,
            fundingsource_name=kwargs["fundingsource_name"],
            funding_id=funding_id,
            bank_name=bank_name,
            type_of_source=type_of_source
        )

        return {'detail': ['Funding source created succussfully']}, status.HTTP_200_OK

    def create_funding_source_manually(self, **kwargs):
        """
        gets bank deatil
        after that makes an api call to add funding source to the customer
        then creates a VerifiedFundingSource
        after that makes another api call to verify this funding source with microdeposit
        """
        customer_obj = kwargs['customer_profile']
        provider = PackageConfigController.get_provider()
        if kwargs['is_admin'] and customer_obj.provider == 'stripe':
            customer_id = customer_obj.account_id
        else:
            customer_id = customer_obj.customer_id
        if provider == "dwolla":
            try:
                dwolla_resp = dwolla_provider.DwollaFundingSource().create_funding_source_manually(
                    customer_id=customer_id,
                    routingNumber=kwargs["routingNumber"],
                    accountNumber=kwargs["accountNumber"],
                    bankAccountType=kwargs["bankAccountType"],
                    fundingsource_name=kwargs["fundingsource_name"],
                )

                funding_id = dwolla_resp.split('/')[-1]
                funding_source_data = self.retrieve_funding_source('dwolla', funding_id)
                bank_name = funding_source_data['bankName']
                type_of_source = funding_source_data['type']

            except Exception as d:
                logger.error(f'error in controller.create_funding_source.dwolla : {d}')
                return {'detail': ['Couldn\'t get dwolla response']}, status.HTTP_400_BAD_REQUEST

        if provider == "stripe":
            try:
                kwargs['customerid'] = customer_id
                if kwargs['is_admin']:
                    stripe_resp = stripe_provider.StripeFundingSource(). \
                        create_funding_source_manually(**kwargs)
                    funding_id = stripe_resp['id']
                    bank_name = stripe_resp['bank_name']
                    type_of_source = stripe_resp['account_type']
                else:
                    kwargs['stripe_account'] = ClientController.get_customer_master_account(
                        user=customer_obj.client.user
                    )
                    payment_method = stripe_provider.paymentmethod.create_bank(
                        **kwargs
                    )
                    funding_id = payment_method['id']
                    bank_name = payment_method['bank_name']
                    type_of_source = 'bank'
            except Exception as d:
                logger.error(f'error in controller.create_funding_source.stripe : {d}')
                return {'detail': ['Couldn\'t get stripe response']}, status.HTTP_400_BAD_REQUEST

        funding_obj = self.create_verified_funding_source(
            customer=customer_obj,
            fundingsource_name=kwargs["fundingsource_name"],
            funding_id=funding_id,
            bank_name=bank_name,
            type_of_source=type_of_source
        )

        try:
            self.verify_microdeposit(funding_obj)
        except Exception as t:
            logger.error(f'error in FundingSourceController.create_funding_source.microdeposit: {str(t)}')

        return {'detail': ['Funding source created succussfully']}, status.HTTP_200_OK

    def update_funding_source(self, funding_source, **kwargs):
        """
        makes an api call to update funding source
        after that updates VerifiedFundingSource obj
        """
        updated_funding_source = self.update_verified_funding_source(funding_source, **kwargs)

        if updated_funding_source.profile.provider in ["dwolla", "dwolla+plaid"]:
            dwolla_provider.DwollaFundingSource().update_funding_source(
                fundingsource_id=updated_funding_source.funding_id,
                name=updated_funding_source.fundingsource_name,
            )

        elif updated_funding_source.profile.provider == "stripe":
            customer_id = funding_source.profile.customer_id
            if not customer_id:
                customer_id = funding_source.profile.account_id
            stripe_provider.StripeFundingSource().update_funding_source(
                customer_id=customer_id,
                bank_acc=funding_source.funding_id,
            )

        return updated_funding_source

    def list_customers_funding_source(self, billing_obj):
        """
        makes an api call and get all funding source of this user
        then check_if_funding_exists after that returns list of VerifiedFundingSource of this user
        """
        provider = billing_obj.provider

        if provider in ["dwolla", "dwolla+plaid"]:
            funding_sources_list = dwolla_provider.DwollaFundingSource(). \
                list_customers_funding_source(billing_obj.customer_id)
        elif provider == "stripe" and billing_obj.account_id:
            funding_sources_list = stripe_provider.StripeFundingSource(). \
                list_customers_funding_source(billing_obj.account_id)
        elif provider == "stripe" and not billing_obj.account_id:
            master_account = ClientController.get_customer_master_account(
                user=billing_obj.client.user
            )
            funding_sources_list = stripe_provider.paymentmethod().list_cards(
                customer_id=billing_obj.customer_id,
                stripe_account=master_account
            )

        for funding_data in funding_sources_list:
            self.check_if_funding_exists(billing_obj, funding_data)

        return self.list_verified_funding_source(billing_obj)

    def retrieve_funding_source(self, provider, funding_id):
        """
        makes an api call and returns detail of a funding source
        """
        if provider in ["dwolla", "dwolla+plaid"]:
            funding_source_data = dwolla_provider.DwollaFundingSource().retrieve_funding_source(funding_id)
        elif provider == "stripe":
            funding_source_data = stripe_provider.StripeFundingSource().retrieve_funding_source(funding_id)

        return funding_source_data

    def get_fundingsource_balance(self, provider, fundingsource_obj):
        """
        makes an api call to get balance of a funding source
        """
        if provider == 'dwolla+plaid':
            balance = plaid_provider.accounts_balance_get(access_token=fundingsource_obj.access_token,
                                                          account_id=fundingsource_obj.account_id)
        elif provider == 'dwolla':
            if fundingsource_obj.type_of_source == 'balance':
                balance = dwolla_provider.DwollaFundingSource().get_fundingsource_balance(fundingsource_obj)
            else:
                balance = None
        elif provider == 'stripe':
            balance = None

        return balance

    def verify_microdeposit(self, funding_obj):
        """
        makes an api call to put funding source in microdepost flow
        """
        if funding_obj.profile.provider == 'dwolla':
            dwolla_provider.DwollaFundingSource().verify_microdeposit(funding_obj.funding_id)
        elif funding_obj.profile.provider == 'dwolla+plaid':
            pass
        elif funding_obj.profile.provider == 'stripe':
            pass

        funding_obj.pending_microdeposit = False
        funding_obj.save()

    def check_if_funding_exists(self, customer_obj, funding_data):
        """it checks if all funding sources are saved in data base else it will create it"""
        provider = customer_obj.provider
        if provider in ['dwolla', 'dwolla+plaid']:
            funding_id = funding_data['id']
            funding_name = funding_data["name"]
            status = funding_data['status']
            if status == "verified":
                pending_microdeposit = False
            if status == "unverified":
                pending_microdeposit = True
            type_of_source = funding_data['type']
            deleted = funding_data['removed']
            if type_of_source == 'balance':
                bank_name = 'dwolla balance'
            else:
                bank_name = funding_data['bankName']

        elif provider == 'stripe':
            type_of_source = funding_data['object']
            funding_id = funding_data['id']
            if type_of_source == 'card':
                funding_name = funding_data['name']
                bank_name = funding_data['brand']

            elif type_of_source == 'payment_method':
                funding_name = funding_data['card']['last4']
                bank_name = funding_data['card']['brand']
            else:
                funding_name = f"{funding_data['account_holder_name']}'s funding"
                bank_name = funding_data['bank_name']
            deleted = False
            pending_microdeposit = False

        funding_obj = VerifiedFundingsource.objects.filter(funding_id=funding_id)
        if not funding_obj:
            self.create_verified_funding_source(
                customer=customer_obj,
                fundingsource_name=funding_name,
                funding_id=funding_id,
                bank_name=bank_name,
                type_of_source=type_of_source,
                deleted=deleted,
                pending_microdeposit=pending_microdeposit
            )
        else:
            self.update_verified_funding_source(
                funding_obj.last(),
                fundingsource_name=funding_name,
                type_of_source=type_of_source,
                deleted=deleted,
                pending_microdeposit=pending_microdeposit
            )

    def is_valid_funding_source(self, funding_source):
        """check if funding source is valid to initiate a payment/transfer"""
        if funding_source.pending_microdeposit == True or funding_source.type_of_source == 'balance' or funding_source.deleted == True:
            return False
        return True

    def create_setup_intent(self, customer_id):
        secret_key = stripe_provider.SetupIntent().create_setup_intent(customer_id)
        return secret_key

    def create_stripe_card_funding_source(self, kwargs, is_admin):
        if not is_admin:
            payment_method = stripe_provider.paymentmethod.create_card(**kwargs)
            kwargs['payment_method_id'] = payment_method['id']
            resp = stripe_provider.paymentmethod.attach(**kwargs)
        else:
            # kwargs['customerid'] = kwargs['stripe_account']
            kwargs['external_account'] = kwargs['card_token']
            resp = stripe_provider.StripeFundingSource(). \
                create_funding_source_manually(**kwargs)

        return resp

    @classmethod
    def list_customer_banks(cls, provider, account_id):
        if provider == 'stripe':
            resp = stripe_provider.StripeFundingSource.list_connected_account_banks(
                account_id
            )
        else:
            resp = None
        return resp

    @classmethod
    def modify_bank_account(cls, provider, *args, **kwargs):
        if provider == 'stripe':
            resp = stripe_provider.StripeFundingSource.modify_bank_account(
                *args, **kwargs
            )
        else:
            resp = None
        return None

    @classmethod
    def modify_customer_payment_method(
            cls, provider, payment_method_token, customer_id, account_id, billing_information):
        if provider == 'stripe':
            resp = stripe_provider.paymentmethod.modify_customer_payment_method(
                payment_method_token, customer_id, account_id
            )
            funding_obj = VerifiedFundingsource.objects.update_or_create(
                profile=billing_information,
                funding_id=payment_method_token,
                type_of_source='card',
            )
            return resp


class TransferController:
    """
    This class holds actions required to interact with Transaction models
    and make api call with Payment provider to create/update/get/delete transfer
    """

    def __init__(self, provider):
        self.provider = provider

    def get_transaction_type(self, user_subscription, type_of_payment, type_of_pledge_funding_source):
        """returns transaction type"""
        if type_of_payment == 'payment_nsf':
            # payment type is pay
            result = str(user_subscription.senderFundingsource.type_of_source) + '-to-' + str(
                type_of_pledge_funding_source)
            return result
        elif type_of_payment == 'one_time_payment_nsf':
            result = str(user_subscription.receiverFundingsource.type_of_source) + '-to-' + str(
                type_of_pledge_funding_source)
            return result

    def create_transaction_obj(self, **kwargs):
        """
        creates a transaction obj
        """
        trasaction_obj = Transaction.objects.create(
            # provider=kwargs['provider'],
            amount=float(kwargs['amount']),
            currency=str(kwargs['currency']),
            source_client=kwargs['source_client'],
            description='pending',
            destination_client=kwargs['destination_client'],
            status=str(kwargs['status']),
            user_subscription=kwargs.get('user_subscription', None),
            transfer_id=kwargs['transfer_id'],
            type_of_payment=kwargs['type_of_transfer'],
            # type_of_transaction = self.get_transaction_type(kwargs['user_subscription'],
            #                          kwargs['type_of_transfer'], kwargs['type_of_destination_funding']),
            correlation_id=kwargs['correlation_id']
        )
        return trasaction_obj

    def get_transaction_obj(self, id=None, transfer_id=None, correlation_id=None):
        """
        return a transaction obj
        """
        try:
            if id:
                return Transaction.objects.get(id=id)
            elif transfer_id:
                return Transaction.objects.get(transfer_id=transfer_id)
            elif correlation_id:
                return Transaction.objects.get(correlation_id=correlation_id)
            raise Exception('obj does\'t exist')
        except Exception as e:
            logger.error(f'error in TransferController.get_transaction_obj: {str(e)}')
            raise Transaction.DoesNotExist

    def transaction_list(self, user, **kwargs):
        """
        filters all transactions of user and returns queryset of transaction
        """
        provider_query = kwargs.get('provider', None)
        source_user_query = kwargs.get('source_user', None)
        destination_user_query = kwargs.get('destination_user', None)
        status_query = kwargs.get('status', None)
        user_subscription_query = kwargs.get('user_subscription', None)
        installment_query = kwargs.get('installment', None)

        transactions_queryset = Transaction.objects.filter(
            Q(source_user=user) | Q(destination_user=user))
        if provider_query:
            transactions_queryset = transactions_queryset.filter(
                provider=provider_query[0])
        if source_user_query:
            transactions_queryset = transactions_queryset.filter(
                source_user__id=source_user_query[0])
        if destination_user_query:
            transactions_queryset = transactions_queryset.filter(
                destination_user__id=destination_user_query[0])
        if status_query:
            transactions_queryset = transactions_queryset.filter(
                status=status_query[0])
        if user_subscription_query:
            transactions_queryset = transactions_queryset.filter(
                user_subscription=user_subscription_query[0])
        if installment_query:
            transactions_queryset = transactions_queryset.filter(
                installment=installment_query[0])

        return transactions_queryset

    def initiate_transfer(self, **kwargs):
        """
        makes an api call to initiate a transfer
        then save the resault in a Transaction obj
        """
        provider = PackageConfigController.get_provider()

        if self.provider == 'dwolla':
            transfer_result = dwolla_provider.DwollaTransfer().initiate_transfer(**kwargs)
            kwargs['amount'] = float(transfer_result['amount']['value'])
            kwargs['currency'] = str(transfer_result['amount']['currency'])
            kwargs['status'] = str(transfer_result['status'])
            kwargs['transfer_id'] = transfer_result['transfer_id']

        elif self.provider == 'stripe':
            try:
                payment_descriptor = PaymentDescriptor.objects.get(
                    payment_type=kwargs['type_of_transfer'])
                descriptor_text = payment_descriptor.descriptor
            except:
                descriptor_text = 'not_set'
            # transfer_result= stripe_provider.StripeTransfer().initiate_transfer(**kwargs)
            transfer_result = stripe_provider.StripePayment().initiate_payment(
                **kwargs)
            transfer_resp = transfer_result['response']
            kwargs['amount'] = float(transfer_resp['amount'] / 100)
            kwargs['currency'] = transfer_resp['currency']
            kwargs['status'] = transfer_resp['status']
            kwargs['transfer_id'] = transfer_resp['id']
            kwargs['transfer_group'] = descriptor_text
            kwargs['type_of_transfer'] = 'stripe_transfer'

        kwargs['source_client'] = kwargs['source'].profile.client
        kwargs['destination_client'] = kwargs['destination'].profile.client
        # kwargs['provider'] = PackageConfigController.get_provider()

        if not transfer_result.get('error'):
            transaction_obj = self.create_transaction_obj(**kwargs)
            return transaction_obj

        logger.error(f'error in TransferController.initiate_transfer: {transfer_result}')
        return 'error'

    def cancel_transfer(self):
        """makes an api call to cancel a pending Transfer"""
        if self.provider == 'dwolla':
            dwolla_provider.DwollaTransfer().cancel_transfer()
        elif self.provider == 'stripe':
            stripe_provider.StripeTransfer().cancel_transfer()

    def list_customer_transfers(self, customer_id):
        """makes an api call and gets all transaction of the customer"""
        if self.provider == 'dwolla':
            dwolla_provider.DwollaTransfer().list_customer_transfers(customer_id)
        elif self.provider == 'stripe':
            stripe_provider.StripeTransfer().list_customer_transfers()

    def retrieve_transfer(self, transfer_id):
        """makes an api call and gets detail of a transfer"""
        if self.provider == 'dwolla':
            transfer_data = dwolla_provider.DwollaTransfer().retrieve_transfer(transfer_id)
        elif self.provider == 'stripe':
            transfer_data = stripe_provider.StripeTransfer().retrieve_transfer(transfer_id)

        return transfer_data

    def get_fee_of_transaction(self, transfer_id):
        """makes an api call and return list of all fees those are take from a transaction"""
        if self.provider in ['dwolla', 'dwolla+plaid']:
            fees_list = dwolla_provider.DwollaTransfer().get_fee_of_transaction(transfer_id)

        return fees_list

    def failed_transfer_fee_logs(self, failed_transfer_obj):
        """gets FeeLogs of a failed Transaction obj"""
        return FeeLogs.objects.filter(transaction=failed_transfer_obj)

    def get_installment_of_transfer(self, transfer_id):
        """
        returns installment of a Transaction obj
        """
        transaction_obj = self.get_transaction_obj(id=transfer_id)
        return transaction_obj.installment

    def get_user_subscription_of_transfer(self, transfer_id):
        """returns UserSubscription of a Transaction obj"""
        installment_obj = self.get_installment_of_transfer(transfer_id)
        return installment_obj.subscription

    def get_failure_reason(self, transfer_id):
        """
        makes an api call to get failure reason of a transfer
        """
        if self.provider in ['dwolla', 'dwolla+plaid']:
            failure_reason = dwolla_provider.DwollaTransfer().get_failure_reason(transfer_id)

        return failure_reason

    def guest_transfer(self, **kwargs):
        resp = stripe_provider.StripePayment().initiate_guest_payment(**kwargs)
        return resp


class PlanCostController:
    def __init__(self, provider, plan_cost):
        self.plan_cost = plan_cost
        self.provider = provider

    def create(self, **kwargs):
        if getattr(settings, "PAYMENT_PROVIDER") == 'stripe':
            product_resp = stripe_provider.Product.create_product(**kwargs)

        subscirption_obj = SubscriptionPlan(
            plan_name=kwargs.get('plan_name')
        )
        subscirption_obj.save()

        plan_cost_obj = PlanCost.objects.create(
            plan=subscirption_obj,
            recurrence_period=kwargs.get('recurrence_period'),
            recurrence_unit=kwargs.get('recurrence_unit'),
            cost=kwargs.get('plan_cost'),
        )
        try:
            plan_cost_obj.provider_sub_id = product_resp['id']
            plan_cost_obj.save()
        except:
            pass
        return plan_cost_obj

    def update_recurrence_period(self, recurrence_period):
        self.plan_cost.recurrence_period = recurrence_period
        self.plan_cost.save()

    def update_recurrence_unit(self, recurrence_unit):
        self.plan_cost.recurrence_unit = recurrence_unit
        self.plan_cost.save()

    def update_cost(self, cost):
        self.plan_cost.cost = cost
        self.plan_cost.save()


class PackageConfigController:
    @classmethod
    def get_provider(self, option=None):
        config = PackageConfig.objects.filter(is_active=True).first()
        if config:
            if not option:
                return config.provider
            elif option == 'subscription_provider':
                return config.subscription_provider
            elif option == 'single_payment_provider':
                return config.single_payment_provider

        print('Provider read from settings')
        return settings.PAYMENT_PROVIDER

    # @classmethod
    # def get_billing_type(self, provider):
    #     if provider == 'stripe_custom':
    #         return 'custom'
    #     elif provider == 'stripe_express':
    #         return 'express'
    #     else:
    #         return 'dwolla'


class SubscriptionScheduleController:
    @classmethod
    def create_sub_sch(cls, subscriber, subscription_owner, plan_cost, start_date,
                       iterations, application_fee_percent, description, interval_unit):

        ### subscription_controller ###

        # Get Customer
        customer_client = ClientController.get_client_by_customer_obj(subscriber)
        customer_billing = BillingInformation.objects.get(client=customer_client)
        customer_id = customer_billing.customer_id

        # Master Account
        rec_client = Client.objects.get(
            user=subscription_owner, client_type='has_account', business=customer_client.business)
        subscription_owner_billing = CustomerController().get_default_billing(
            client=rec_client
        )
        stripe_account = subscription_owner_billing.account_id

        # Price
        price_id = stripe_provider.subscription.get_price_id(
            plan_cost.provider_product_id, stripe_account)

        ### subscription_controller ###

        # start_date
        if start_date == "now":
            usub_start_date = datetime.today()
            schedule_start_date = "now"
        else:
            usub_start_date = start_date
            schedule_start_date = start_date

        # Create Subscription Object
        user_subscription = UserSubscription(
            user=subscription_owner_billing,
            subscriber=customer_billing,
            subscription=plan_cost,
            date_billing_start=usub_start_date,
            cancelled=False,
            active=False
        )

        # Schedule Kwargs
        schedule_kwargs = {}
        schedule_kwargs['customer'] = customer_id
        schedule_kwargs['stripe_account'] = stripe_account
        schedule_kwargs['start_date'] = schedule_start_date
        schedule_kwargs['end_behavior'] = 'cancel'
        schedule_kwargs['phases'] = [
            {"items": [{
                "price": price_id,
                "quantity": 1
            }],
                "iterations": iterations,
                "application_fee_percent": application_fee_percent,
            }]
        schedule_kwargs['default_settings'] = {
            "description": description
        }
        # check the provider
        subscription_schedule = stripe_provider.SubscriptionSchedule.create(
            **schedule_kwargs)

        # add the data to user_subscription obj
        # logger.info("subscription_schedulee")
        # logger.info(subscription_schedule)
        try:
            if start_date == "now":
                user_subscription.provider_usub_id = subscription_schedule.subscription
            else:
                user_subscription.provider_schedule_id = subscription_schedule['id']
            user_subscription.save()
        except Exception as e:

            logger.exception(f'subcc {str(e)}')

        # fix this
        InstallmentController.create_subscription_installments(
            user_subscription, interval_unit, iterations)

        return user_subscription, subscription_schedule
