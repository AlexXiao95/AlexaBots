"""

"""
import argparse
import boto3
from boto3.dynamodb.conditions import Key, Attr

def make_user_info_item(user_id,**kwargs):
    """take user_id and kwargs, return item for UserInfo table

    see schema for enumeration of values that these can take
    """
    user_info_item = {
        'user_id' : user_id,
        'work_address': kwargs.get('work_address'),
        'work_zip': kwargs.get('work_zip'),
        'home_address': kwargs.get('home_address'),
        'home_zip': kwargs.get('home_zip'),
        'travel_method': kwargs.get('travel_method'),
    }
    return user_info_item


def get_item_by_key(table, partition_key, value):
    """query a given table and partition key for a value, return response"""
    # notice that the return is a list of the dicts
    # TODO: what if multiple record returns? like multiple history. Currently use the last one
    response = table.query(KeyConditionExpression=Key(partition_key).eq(value))
    return response['Items']


def make_user_previous_recommendation_item(session):
    """with the session, to get the session attribute and
    add the user_id to the session_attribute
    """
    # TODO: put some default parameters to the session_attribute when attribute
    # initialization.(create an attribute initializer)
    item = session['attributes']
    this_user_id = session["user"]["userId"]
    item['user_id'] = this_user_id
    return item


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument('dummy', help='')
    args = p.parse_args()
    