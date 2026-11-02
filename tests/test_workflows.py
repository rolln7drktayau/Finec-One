"""Executable integration tests for simulated banking and maker/checker controls."""
import pytest
from fastapi.testclient import TestClient
from app import database
from app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "isolated.sqlite3")
    with TestClient(app) as test:
        yield test


def token(client, username):
    result = client.post("/api/auth/login", json={"username":username,"password":"Demo2026!"})
    assert result.status_code == 200, result.text
    return {"Authorization":"Bearer "+result.json()["token"]}


def get(client, path, headers):
    res = client.get(path, headers=headers)
    assert res.status_code == 200, res.text
    return res.json()


def post(client, path, headers, body):
    return client.post(path, headers=headers, json=body)


def test_seed_is_balanced(client):
    admin=token(client,"admin")
    check=get(client,"/api/reports/check",admin)
    assert check["balanced"] and check["audit_chain_valid"]
    assert check["entries_checked"] >= 20
    assert get(client,"/api/reports/dashboard",admin)["kpis"]["branches"] == 7


def test_deposit_transfer_and_atomic_negative_balance(client):
    teller=token(client,"agent")
    accounts=get(client,"/api/accounts",teller)
    src=next(a for a in accounts if a['customer_id']==1 and a['product']=='savings')
    dst=next(a for a in accounts if a['customer_id']==2 and a['product']=='savings')
    created=post(client,"/api/operations",teller,{
        "kind":"deposit","amount":300000,"destination_account_id":src['id'],"request_key":"test-deposit-001"})
    assert created.status_code == 201, created.text
    # Replaying the same idempotency key cannot post a second journal.
    replay=post(client,"/api/operations",teller,{
        "kind":"deposit","amount":300000,"destination_account_id":src['id'],"request_key":"test-deposit-001"})
    assert replay.json()['id']==created.json()['id']
    now=next(a for a in get(client,"/api/accounts",teller) if a['id']==src['id'])
    assert now['balance']==src['balance']+300000
    bad=post(client,"/api/operations",teller,{
        "kind":"transfer","amount":99999999,"source_account_id":src['id'],"destination_account_id":dst['id']})
    assert bad.status_code == 400
    small=post(client,"/api/operations",teller,{
        "kind":"transfer","amount":10000,"source_account_id":src['id'],"destination_account_id":dst['id']})
    assert small.status_code == 201 and small.json()['status']=='posted'
    assert get(client,"/api/reports/check",teller)['balanced']


def test_two_person_high_value_transfer(client):
    teller=token(client,"agent")
    manager=token(client,"manager")
    accounts=get(client,"/api/accounts",teller)
    src=next(a for a in accounts if a['customer_id']==2 and a['product']=='savings')
    dst=next(a for a in accounts if a['customer_id']==1 and a['product']=='savings')
    op=post(client,"/api/operations",teller,{
        "kind":"transfer","amount":1000000,"source_account_id":src['id'],"destination_account_id":dst['id']})
    assert op.status_code==201,op.text
    assert op.json()['status']=='pending'
    assert post(client,f"/api/operations/{op.json()['id']}/decision",teller,{"decision":"approve"}).status_code==403
    approved=post(client,f"/api/operations/{op.json()['id']}/decision",manager,{"decision":"approve"})
    assert approved.status_code==200,approved.text
    assert approved.json()['status']=='posted'
    assert get(client,"/api/reports/check",manager)['balanced']


def test_kyc_account_creation_and_separation(client):
    teller=token(client,"agent")
    compliance=token(client,"conformite")
    cid=8   # Synthetic unverified fixture
    acc=post(client,"/api/accounts",teller,{"customer_id":cid,"product":"savings"})
    assert acc.status_code==400
    verify=client.patch(f"/api/customers/{cid}/kyc",headers=compliance,json={"status":"verified","risk_level":"HIGH"})
    assert verify.status_code==200
    opened=post(client,"/api/accounts",teller,{"customer_id":cid,"product":"savings"})
    assert opened.status_code==201,opened.text
    acct_id=opened.json()['id']
    frozen=client.patch(f"/api/accounts/{acct_id}/status",headers=compliance,json={"status":"frozen"})
    assert frozen.status_code==200
    deposit=post(client,"/api/operations",teller,{"kind":"deposit","amount":5000,"destination_account_id":acct_id})
    assert deposit.status_code==400


def test_loan_disbursement_repayment_and_csv(client):
    credit=token(client,"credit")
    manager=token(client,"manager")
    teller=token(client,"agent")
    accounts=get(client,"/api/accounts",credit)
    account=next(a for a in accounts if a['customer_id']==2 and a['product']=='savings')
    application=post(client,"/api/loans",credit,{"customer_id":2,"account_id":account['id'],
                                                 "product":"school","principal":200000,"rate":0,"term_months":10})
    assert application.status_code==201,application.text
    loan_id=application.json()['id']
    assert post(client,f"/api/loans/{loan_id}/decision",credit,{"decision":"approve"}).status_code==403
    active=post(client,f"/api/loans/{loan_id}/decision",manager,{"decision":"approve"})
    assert active.status_code==200,active.text
    assert active.json()['status']=='active'
    payment=post(client,f"/api/loans/{loan_id}/repay",teller,{"amount":200000})
    assert payment.status_code==200,payment.text
    assert payment.json()['outstanding']==0
    assert get(client,"/api/reports/check",teller)['balanced']
    response=client.get("/api/reports/export/ledger",headers=teller)
    assert response.status_code==200 and 'JE-' in response.text


def test_auditor_read_only(client):
    auditor=token(client,"auditeur")
    assert get(client,"/api/audit",auditor)
    attempt=post(client,"/api/customers",auditor,{"full_name":"Synthetic X","phone":"+237600000000","branch_id":1})
    assert attempt.status_code==403


def test_compliance_alert_review_and_audit_integrity(client):
    compliance = token(client, "conformite")
    alerts = get(client, "/api/alerts", compliance)
    assert len(alerts) >= 1  # Seeded high-value fictional transaction
    open_alert = next(a for a in alerts if a['status'] == 'open')
    updated = client.patch(f"/api/alerts/{open_alert['id']}",
                           headers=compliance, json={'status':'reviewed'})
    assert updated.status_code == 200
    assert updated.json()['status'] == 'reviewed'
    assert get(client, "/api/reports/check", compliance)['audit_chain_valid']


def test_rejected_workflow_keeps_balances_and_blocks_reused_keys(client):
    teller = token(client, "agent")
    manager = token(client, "manager")
    accounts = get(client, "/api/accounts", teller)
    src = next(a for a in accounts if a['customer_id'] == 2 and a['product'] == 'savings')
    dst = next(a for a in accounts if a['customer_id'] == 1 and a['product'] == 'savings')
    request = {'kind':'transfer', 'amount':1_100_000,
               'source_account_id':src['id'], 'destination_account_id':dst['id'],
               'request_key':'idempotency-example'}
    sent = post(client, '/api/operations', teller, request)
    assert sent.status_code == 201 and sent.json()['status'] == 'pending'
    changed = {**request,'amount':1_200_000}
    assert post(client, '/api/operations', teller, changed).status_code == 400
    refused = post(client, f"/api/operations/{sent.json()['id']}/decision", manager,
                   {'decision':'reject'})
    assert refused.status_code == 200 and refused.json()['status'] == 'rejected'
    after = get(client, "/api/accounts", teller)
    assert next(a for a in after if a['id']==src['id'])['balance'] == src['balance']
    assert next(a for a in after if a['id']==dst['id'])['balance'] == dst['balance']
    assert get(client, "/api/reports/check", teller)['balanced']
