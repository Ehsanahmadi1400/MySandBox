import logging
import requests
from uuid import uuid4
from .abstract_classes import *
from payment.utils import (
    get_current_server,
    three_letter_abbreviation_of_the_country
)
from payment.utils import get_current_server
from typing import Literal

from django.conf import settings


logger = logging.getLogger(__file__)

error_logs_prefix = 'Payment Package error in:'


bank_account_type = Literal[
    'CHECKING',
    'SAVINGS',
]

bank_account_corporate = Literal[
    'PERSONAL',
    'CORPORATE',
]


class HelcimClinet(AbstractClient):

    @classmethod
    def create_customer(
        cls,
        account_id,
        **kwargs
    ):
        api_kwargs = dict()
        if not (kwargs.get('first_name',None) or kwargs.get('last_name', None)):
            raise Exception(
                f'{error_logs_prefix} {cls.create_customer.__qualname__} '
                f'At least one of first_name or last_name must be defined'
            )
        if kwargs.get('first_name', False) and kwargs.get('last_name', False):
            api_kwargs['contactName'] = kwargs['first_name'] + ' ' + kwargs['last_name']
        elif kwargs.get('first_name', None):
            api_kwargs['contactName'] = kwargs['first_name']
        elif kwargs.get('last_name', None):
            api_kwargs['contactName'] = kwargs['last_name']

        if kwargs.get("phone", None):
            api_kwargs['cellPhone'] = kwargs["phone"]

        if kwargs.get('address1', False) and kwargs.get('postal_code', False)\
            and kwargs.get("state", False) and kwargs.get('country', False):
            api_kwargs['billingAddress'] = dict()
            api_kwargs['billingAddress']['name'] = api_kwargs['contactName']
            api_kwargs['billingAddress']['street1'] = kwargs['address1']
            api_kwargs['billingAddress']['postalCode'] = \
                kwargs['postal_code']
            api_kwargs['billingAddress']['province'] = \
                kwargs['state']
            api_kwargs['billingAddress']['country'] = \
                kwargs['country']

        if api_kwargs.get('billingAddress', False):
            if kwargs.get("phone", None):
                api_kwargs['billingAddress']['phone'] = kwargs["phone"]
            if kwargs.get('address2', None):
                api_kwargs['billingAddress']['street2'] = kwargs["address2"]
            if kwargs.get('city', None):
                api_kwargs['billingAddress']['city'] = kwargs["city"]
            if kwargs.get('email', None):
                api_kwargs['billingAddress']['email'] = kwargs["email"]
            
        url = "https://api.helcim.com/v2/customers/"

        headers = {
                "accept": "application/json",
                "content-type": "application/json",
                "api-token": account_id,
            }
        if settings.HELCIM_PARTNER_TOKEN:
            headers['partner-token'] = settings.HELCIM_PARTNER_TOKEN
        
        response = requests.post(url, json=api_kwargs, headers=headers)

        json_response = response.json()
        if json_response.get('errors', None):
            raise Exception(
                f'{error_logs_prefix} {cls.create_customer.__qualname__} '
                f'{str(json_response["errors"])}'
            )
        else:
            return json_response

    @classmethod
    def create_account_link(
        cls,
        account_id: str,
        **api_kwargs
    ):
        return {
            "object": "helcim_login_link",
            "url": "https://hsso.helcim.com/login/"
        }

    @classmethod
    def create_bank_account(
        cls,
        account_id,
        account_number,
        first_name,
        last_name,
        address,
        city,
        state,
        postal_code,
        helcim_customer_code,
        country: str = 'Canada',
        currency: str = 'CAD',
        bank_id_number = None, # required for Canadian in helcim
        transit_number = None, # required for Canadian in helcim
        routing_number = None, # required for US users
        company_name = None,
        account_type: bank_account_type = 'CHECKING',
        account_corporate: bank_account_corporate = 'PERSONAL',
        **api_kwargs
    ):
        api_kwargs = {
            "bankData": {
                "firstName": first_name,
                "lastName": last_name,
                "bankAccountNumber": account_number,
                "accountType": account_type,
                "accountCorporate": account_corporate,
                "bankIdNumber": bank_id_number,
                "transitNumber": transit_number,
                "routingNumber": routing_number,
                "streetAddress": address,
                "city": city,
                "country": three_letter_abbreviation_of_the_country(country),
                "province": state,
                "postalCode": postal_code
            },
            "ipAddress": get_current_server(),
            "currency": currency,
            "amount": 0,
            "customerCode": helcim_customer_code
        }
        if api_kwargs.get('ipAddress', None):
            api_kwargs["ipAddress"] = api_kwargs["ipAddress"]
        else:
            api_kwargs["ipAddress"] = get_current_server()
        if company_name:
            api_kwargs['bankData']['companyName'] = company_name
        else:
            api_kwargs['bankData']['companyName'] = last_name

        headers = {
            "accept": "application/json",
            "idempotency-key": str(uuid4())[:25],
            "content-type": "application/json",
            "api-token": account_id
        }
        if settings.HELCIM_PARTNER_TOKEN:
            headers['partner-token'] = settings.HELCIM_PARTNER_TOKEN
        url = "https://api.helcim.com/v2/payment/withdraw"
        response = requests.post(url, json=api_kwargs, headers=headers)

        json_response = response.json()
        if json_response.get('errors', None):
            raise Exception(
                f'{error_logs_prefix} {cls.create_bank_account.__qualname__} '
                f'{str(json_response["errors"])}'
            )
        else:
            return json_response

    @classmethod
    def get_customer_cards(
        cls,
        account_id: str,
        customer_id: str,
        **api_kwargs
    ):
        url = f"https://api.helcim.com/v2/customers/{customer_id}/cards"
        headers = {
            "accept": "application/json",
            "api-token": f"{account_id}"
        }
        if settings.HELCIM_PARTNER_TOKEN:
            headers['partner-token'] = settings.HELCIM_PARTNER_TOKEN
        response = requests.get(url, headers = headers)
        json_response = response.json()
        if isinstance(json_response, dict) and json_response.get('errors', None):
            raise Exception(
                f'{error_logs_prefix} {cls.get_customer_cards.__qualname__} '
                f'{str(json_response["errors"])}'
            )
        else:
            cards = list()
            for item in json_response:
                payment_method = {
                    'funding_id': item['cardToken'],
                    'last4': item['cardF6L4'][-4:],
                    'exp_month': item['cardExpiry'][:2],
                    'exp_year': item['cardExpiry'][2:],
                    'brand': None,
                }
                cards.append(payment_method)
            return cards


class HelcimPayment(AbstractPayment):
    
    @classmethod
    def payment(
        cls,
        account_id: str,
        amount: float,
        funding_id: str,
        customer_id: str = None,
        customer_code: str = None,
        currency: str = 'CAD',
        **api_kwargs
    ):
        url = "https://api.helcim.com/v2/payment/purchase"
        payload = {
            "cardData": { "cardToken": funding_id },
            "currency": currency,
            "amount": str(amount),
            "customerCode": customer_code,
        }
        if api_kwargs.get('ipAddress', None):
            payload["ipAddress"] = api_kwargs["ipAddress"]
        else:
            payload["ipAddress"] = get_current_server()
        headers = {
            "accept": "application/json",
            "idempotency-key": str(uuid4())[:25],
            "content-type": "application/json",
            "api-token": account_id,
        }
        if settings.HELCIM_PARTNER_TOKEN:
            headers['partner-token'] = settings.HELCIM_PARTNER_TOKEN
        response = requests.post(url, json=payload, headers=headers)
        json_response = response.json()
        if json_response.get('errors', None):
            logger.exception(
                f'{error_logs_prefix} {cls.payment.__qualname__} '
                f'{str(json_response["errors"])}'
            )
            return {'status': 'ERROR'}
        else:
            return json_response

    @classmethod
    def get_invoice_by_invoice_number(
        cls,
        account_id: str,
        invoice_number: str,
    ):
        headers = {
            "accept": "application/json",
            "idempotency-key": str(uuid4())[:25],
            "content-type": "application/json",
            "api-token": account_id
        }
        url = f"https://api.helcim.com/v2/invoices/?invoiceNumber={invoice_number}"
        response = requests.get(url, headers=headers)
        invoice_data = response.json()[0]
        return invoice_data
    
    @classmethod
    def get_invoice_by_invoice_id(
        cls,
        account_id: str,
        invoice_id: str,
    ):
        headers = {
            "accept": "application/json",
            "idempotency-key": str(uuid4())[:25],
            "content-type": "application/json",
            "api-token": account_id
        }
        url = f"https://api.helcim.com/v2/invoices/{invoice_id}"
        response = requests.get(url, headers=headers)
        invoice_data = response.json()
        return invoice_data


class HelcimTransfer(AbstractTransfer):
    
    @classmethod
    def transfer(
        cls,
        account_id,
        helcim_customer_code,
        amount: float,
        bank_token: str,
        currency: str = 'CAD',
        **api_kwargs
    ):
        url = "https://api.helcim.com/v2/payment/withdraw"

        payload = {
            "bankData": { "bankToken": bank_token },
            "currency": currency,
            "amount": amount,
            "customerCode": helcim_customer_code,
        }
        if api_kwargs.get('ipAddress', None):
            payload["ipAddress"] = api_kwargs["ipAddress"]
        else:
            payload["ipAddress"] = get_current_server()
        headers = {
            "accept": "application/json",
            "idempotency-key": str(uuid4())[:25],
            "content-type": "application/json",
            "api-token": account_id
        }
        if settings.HELCIM_PARTNER_TOKEN:
            headers['partner-token'] = settings.HELCIM_PARTNER_TOKEN

        response = requests.post(url, json=payload, headers=headers)
        json_response = response.json()

        if json_response.get('errors', None):
            raise Exception(
                f'{error_logs_prefix} {cls.transfer.__qualname__} '
                f'{str(json_response["errors"])}'
            )
        else:
            return json_response
