

class AbstractTransfer:
    def __init__(self):
        pass

    def initiate_transfer(self):
        pass

    def retrieve_transfer(self):
        pass

    def list_customer_transfers(self):
        pass

    def cancel_transfer(self):
        pass


class AbstractRecurringTransfer:
    def __init__(self):
        pass

    def initiate_transfer(self):
        pass

    def retrieve_transfer(self):
        pass

    def list_customer_transfers(self):
        pass

    def cancel_transfer(self):
        pass


class AbstractPayment:
    def __init__(self):
        pass

    def initiate_payment(self):
        pass

    def retrieve_payment(self):
        pass

    def list_payment(self):
        pass

    def update_payment(self):
        pass


class AbstractRecurringPayment:
    def __init__(self):
        pass

    def initiate_payment(self):
        pass

    def retrieve_payment(self):
        pass

    def list_payment(self):
        pass

    def update_payment(self):
        pass


class AbstractFundingSource:
    def __init__(self):
        pass

    def create_funding_source(self):
        pass

    def create_funding_source_manually(self):
        pass

    def update_funding_source(self):
        pass

    def list_customers_funding_source(self):
        pass

    def retrieve_funding_source(self):
        pass

    def get_fundingsource_balance(self):
        pass

    def verify_microdeposit(self):
        pass


class AbstractClient:
    def __init__(self):
        pass     

    @classmethod
    def create_customer(cls):
        pass

    @classmethod
    def retrieve_customer(cls, customer_id):
        pass

    @classmethod
    def list_customers(cls):
        pass

    @classmethod
    def update_customer(cls, customer_id):
        pass

    @classmethod
    def delete_customer(cls, customer_id):
        pass
    
    @classmethod
    def create_merchant(cls):
        pass

    @classmethod
    def retrieve_merchant(cls, merchant_id):
        pass

    @classmethod
    def list_merchants(cls):
        pass

    @classmethod
    def update_merchant(cls, merchant_id):
        pass

    @classmethod
    def delete_merchant(cls, merchant_id):
        pass


class AbstractWebhook:
    def __init__(self):
        pass

    def create_webhook(self):
        pass

    def retrieve_webhook(self, webhook_id):
        pass

    def update_webhook(self, webhook_id, webhook_status):
        pass
            
    def list_webhooks(self):
        pass

    def delete_webhook(self, webhook_id):
        pass