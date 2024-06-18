import json
def send_information_order(total_price, product_list, email):

    try:
        print("functin is called")
        return json.dumps({"status": "success", "message": "Information of the order is sent to your email"})

    except:
        return False