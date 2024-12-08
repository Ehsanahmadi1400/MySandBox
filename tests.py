
def test_helcim_factory():
    factory = HelcimFactory()

    # Test Customer Client
    customer_client = factory.create_customer_client()
    customer_client.create_customer(name="John Doe")
    customer_client.retrieve_customer(customer_id="12345")
    customer_client.update_customer(customer_id="12345", name="Jane Doe")
    customer_client.delete_customer(customer_id="12345")

    # Test Merchant Client
    merchant_client = factory.create_merchant_client()
    merchant_client.create_merchant(name="Doe Enterprises")
    merchant_client.retrieve_merchant(merchant_id="67890")
    merchant_client.update_merchant(merchant_id="67890", name="Doe Enterprises Inc.")
    merchant_client.delete_merchant(merchant_id="67890")

    # Test Single Payment Strategy
    single_payment_strategy = factory.create_single_payment_strategy()
    single_payment_strategy.initiate_payment(amount=100.00, currency="USD")
    single_payment_strategy.retrieve_payment(payment_id="pay_001")
    single_payment_strategy.update_payment(payment_id="pay_001", amount=110.00)

    # Test Recurring Payment Strategy
    recurring_payment_strategy = factory.create_recurring_payment_strategy()
    recurring_payment_strategy.initiate_payment(amount=50.00, currency="USD", interval="monthly")
    recurring_payment_strategy.retrieve_payment(payment_id="rec_pay_001")
    recurring_payment_strategy.update_payment(payment_id="rec_pay_001", amount=55.00)

    # Test Single Transfer Strategy
    single_transfer_strategy = factory.create_single_transfer_strategy()
    single_transfer_strategy.initiate_transfer(amount=200.00, currency="USD", recipient="John Doe")
    single_transfer_strategy.retrieve_transfer(transfer_id="trans_001")
    single_transfer_strategy.cancel_transfer(transfer_id="trans_001")

    # Test Recurring Transfer Strategy
    recurring_transfer_strategy = factory.create_recurring_transfer_strategy()
    recurring_transfer_strategy.initiate_transfer(amount=150.00, currency="USD", recipient="Jane Doe",
                                                  interval="weekly")
    recurring_transfer_strategy.retrieve_transfer(transfer_id="rec_trans_001")
    recurring_transfer_strategy.cancel_transfer(transfer_id="rec_trans_001")


# Run the test
test_helcim_factory()
