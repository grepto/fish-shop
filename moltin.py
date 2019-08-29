import os
import logging

from dotenv import load_dotenv
import requests

load_dotenv()
MOLTIN_CLIENT_ID = os.getenv('MOLTIN_CLIENT_ID')
MOLTIN_SECRET = os.getenv('MOLTIN_SECRET')
MOLTIN_ENDPOINT = 'https://api.moltin.com'
MOLTIN_API_VERSION = 'v2'

logger = logging.getLogger('moltin')


def get_token():
    data = {
        'client_id': MOLTIN_CLIENT_ID,
        'client_secret': MOLTIN_SECRET,
        'grant_type': 'client_credentials'
    }

    response = requests.post(f'{MOLTIN_ENDPOINT}/oauth/access_token', data=data)
    logger.debug(response.json())

    response.raise_for_status()

    return f'{response.json()["token_type"]} {response.json()["access_token"]}'


def get_products():
    headers = {
        'Authorization': get_token(),
    }

    url = f'{MOLTIN_ENDPOINT}/{MOLTIN_API_VERSION}/products'

    response = requests.get(url, headers=headers)
    logger.debug(response.json())

    response.raise_for_status()

    return response.json()['data']


def get_product(product_id):
    headers = {
        'Authorization': get_token(),
    }

    url = f'{MOLTIN_ENDPOINT}/{MOLTIN_API_VERSION}/products/{product_id}'
    response = requests.get(url, headers=headers)
    logger.debug(response.json())

    response.raise_for_status()

    data = response.json()['data']

    product = {
        'id': data['id'],
        'name': data['name'],
        'description': data['description'],
        'price': data['price'][0]['amount'],
        'price_formatted': data['meta']['display_price']['with_tax']['formatted'],
        'availability': data['meta']['stock']['level'],
        'image_id': data['relationships']['main_image']['data']['id'],
    }

    return product


def add_cart_item(customer_id, product_id, quantity=1):
    headers = {
        'Authorization': get_token(),
        'Content-Type': 'application/json',
    }

    data = {
        'data': {
            'id': product_id,
            'type': 'cart_item',
            'quantity': quantity
        }
    }

    url = f'{MOLTIN_ENDPOINT}/{MOLTIN_API_VERSION}/carts/:{customer_id}/items'
    response = requests.post(url, headers=headers, json=data)
    logger.debug(response.json())

    response.raise_for_status()


def remove_cart_item(customer_id, cart_item_id):
    headers = {
        'Authorization': get_token(),
        'Content-Type': 'application/json',
    }
    url = f'{MOLTIN_ENDPOINT}/{MOLTIN_API_VERSION}/carts/:{customer_id}/items/{cart_item_id}'
    response = requests.delete(url, headers=headers)
    logger.debug(response.json())

    response.raise_for_status()


def get_cart(customer_id):
    headers = {
        'Authorization': get_token(),
        'Content-Type': 'application/json',
    }
    url = f'{MOLTIN_ENDPOINT}/{MOLTIN_API_VERSION}/carts/:{customer_id}/items'
    response = requests.get(url, headers=headers)
    logger.debug(response.json())

    response.raise_for_status()

    products = []
    for product in response.json()['data']:
        product_info = {
            'id': product['id'],
            'product_id': product['product_id'],
            'name': product['name'],
            'description': product['description'],
            'quantity': product['quantity'],
            'unit_price': product['meta']['display_price']['with_tax']['unit']['formatted'],
            'total_price': product['meta']['display_price']['with_tax']['value']['formatted'],
        }
        products.append(product_info)
    total_price = response.json()['meta']['display_price']['with_tax']['formatted']

    return {'products': products, 'total_price': total_price}


def delete_cart(customer_id):
    headers = {
        'Authorization': get_token(),
        'Content-Type': 'application/json',
    }
    url = f'{MOLTIN_ENDPOINT}/{MOLTIN_API_VERSION}/carts/:{customer_id}'
    response = requests.delete(url, headers=headers)
    logger.debug(response.json())

    response.raise_for_status()


def get_product_image_url(image_id):
    headers = {
        'Authorization': get_token(),
        'Content-Type': 'application/json',
    }
    url = f'{MOLTIN_ENDPOINT}/{MOLTIN_API_VERSION}/files/{image_id}'
    response = requests.get(url, headers=headers)
    logger.debug(response.json())

    response.raise_for_status()

    return response.json()['data']['link']['href']


def get_customer(customer_id=None, email=None):
    headers = {
        'Authorization': get_token(),
        'Content-Type': 'application/json',
    }
    if customer_id:
        url = f'{MOLTIN_ENDPOINT}/{MOLTIN_API_VERSION}/customers/:{customer_id}'
    elif email:
        url = f'{MOLTIN_ENDPOINT}/{MOLTIN_API_VERSION}/customers?filter=eq(email,{email})'
    else:
        return
    response = requests.get(url, headers=headers)
    logger.debug(response.json())

    response.raise_for_status()

    return response.json()['data']


def add_customer(name, email):
    headers = {
        'Authorization': get_token(),
        'Content-Type': 'application/json',
    }

    data = {
        'data': {
            'type': 'customer',
            'name': name,
            'email': email,
        }
    }

    url = f'{MOLTIN_ENDPOINT}/{MOLTIN_API_VERSION}/customers'

    response = requests.post(url, headers=headers, json=data)
    logger.debug(response.json())

    error = response.json().get('errors', [])

    customer_id = None

    if not error:
        customer_id = response.json()['data']['id']
    elif error[0].get('title') == 'Duplicate email':
        customer_id = get_customer(email=email)[0]['id']

    return customer_id


def main():
    products = get_products()
    # print(products)
    selected_product = products[0]
    customer_id = '112812571'
    # print(selected_product['id'])
    # product = get_product(selected_product['id'])
    # print(get_product_image_url(product['image_id']))

    # delete_cart(customer_id)
    # add_product_to_cart(customer_id, selected_product['id'], 5)
    # print(get_cart(customer_id))
    # remove_cart_item(customer_id, 'f619db5d-762c-4411-97e7-ddc6d518e494')
    # print()
    # print(get_cart(customer_id))
    print(add_customer('sasha', '123olo@tr3lo111.lo'))
    # print(get_customer(email='ololo@trolo121.lo'))


if __name__ == '__main__':
    main()
