from collections import defaultdict

def simplify_debts(raw_transactions, user_map):
    net_balances=defaultdict(float)

    for t in raw_transactions:
        net_balances[t["borrower_id"]]-=t["amount"]
        net_balances[t["payer_id"]]+=t["amount"]

    debtors=[]
    creditors=[]

    for user_id, balance in net_balances.items():
        if balance< -0.01:
            debtors.append([user_id, -balance])
        elif balance >0.01:
            creditors.append([user_id, balance])
    
    debtors.sort(key=lambda x:x[1], reverse=True)
    creditors.sort(key=lambda x:x[1], reverse=True)

    simplified=[]
    i,j=0,0

    while i<len(debtors) and j<len(creditors):
        debtor_id, debt_amount= debtors[i]
        creditor_id, credit_amount=creditors[j]

        settle_amount=min(debt_amount, credit_amount)

        borrower_name=user_map.get(debtor_id, f"User {debtor_id}")
        payer_name= user_map.get(creditor_id, f"User {creditor_id}")


        simplified.append({
            "borrower_id":debtor_id,
            "payer_id":creditor_id,
            "amount":round(settle_amount,2),
            "message": f"{borrower_name} owes {payer_name} Rs{round(settle_amount,2)}"
        })

        debtors[i][1] -=settle_amount
        creditors[j][1] -=settle_amount

        if debtors[i][1]< 0.01: i+=1
        if creditors[j][1] < 0.01: j+=1

    return simplified