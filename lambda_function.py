"""
TODO: add description
"""

import logging
import random
import time
import boto3
from boto3.dynamodb.conditions import Key, Attr
from dynamo_db.dynamo import *
from utils.query_api import *

# --------------- Load DynamoDB settings ----------------------

dynamodb = boto3.resource('dynamodb')
user_info = dynamodb.Table('UserInfo')
previous_recs = dynamodb.Table('PreviousRecommendations')

# Get time, and we can use this info to infer if the user want places which is open now.
# return time of current time zone, sample return:
# time.struct_time(tm_year=2018, tm_mon=5, tm_mday=15, tm_hour=14, tm_min=53, tm_sec=20, tm_wday=1, tm_yday=135, tm_isdst=1)
time_array = time.localtime()
tm_hour = time_array[3]
tm_min = time_array[4]
tm_wday = time_array[6]

# --------------- Helpers that build all of the responses ----------------------

def build_speechlet_response(title, output, reprompt_text, should_end_session):
    return {
        'outputSpeech': {
            'type': 'PlainText',
            'text': output
        },
        'card': {
            'type': 'Simple',
            'title': "SessionSpeechlet - " + title,
            'content': "SessionSpeechlet - " + output
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': reprompt_text
            }
        },
        'shouldEndSession': should_end_session
    }


def build_response(session_attributes, speechlet_response):
    return {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': speechlet_response
    }


# --------------- Functions that control the skill's behavior ------------------
def set_default_zip_or_address(intent, session):

    """
    Sets the users default work or home zipcode.
    """

    card_title = intent['name']
    session_attributes = session['attributes']
    should_end_session = False
    this_user_id = session["user"]["userId"]
    session_attributes['this_user_id'] = this_user_id

    if 'value' in intent['slots']['homezip']:
        new_home_zip = intent['slots']['homezip']['value']

        key_value = dict({'user_id': this_user_id})
        attUpdate_value = dict({'home_zip': {'Value': new_home_zip}})

        user_info.update_item(Key=key_value, AttributeUpdates=attUpdate_value )
        session_attributes['which_zip'] = 'home and work' if (session_attributes.get('which_address') == 'work') else 'home'

    if 'value' in intent['slots']['workzip']:
        new_work_zip = intent['slots']['workzip']['value']

        key_value = dict({'user_id': this_user_id})
        attUpdate_value = dict({'work_zip': {'Value': new_work_zip}})

        user_info.update_item(Key=key_value, AttributeUpdates=attUpdate_value)
        session_attributes['which_zip'] = 'home and work' if (session_attributes.get('which_zip') == 'home') else 'work'

    if 'value' in intent['slots']['homeaddress']:
        new_home_address = intent['slots']['homeaddress']['value']

        key_value = dict({'user_id': this_user_id})
        attUpdate_value = dict({'home_address': {'Value': new_home_address}})

        user_info.update_item(Key=key_value, AttributeUpdates=attUpdate_value)
        session_attributes['which_address'] = 'home and work' if (session_attributes.get('which_address') == 'work') else 'home'

    if 'value' in intent['slots']['workaddress']:
        new_work_address = intent['slots']['workaddress']['value']

        key_value = dict({'user_id': this_user_id})
        attUpdate_value = dict({'work_address': {'Value': new_work_address}})

        user_info.update_item(Key=key_value, AttributeUpdates=attUpdate_value)
        session_attributes['which_address'] = 'home and work' if (session_attributes.get('which_address') == 'home') else 'work'

    return build_output(session_attributes, card_title, should_end_session)


def get_welcome_response():
    """ If we wanted to initialize the session to have some attributes we could
    add those here
    """

    session_attributes = {}
    card_title = "Welcome"
    speech_output = "Welcome back to Mos Eisley Cantina! Tell me what kind " \
                    "of cuisine you are looking for."
    # If the user either does not reply to the welcome message or says something
    # that is not understood, they will be prompted again with this text.
    reprompt_text = "I can recommend any types of cuisines. You can say things like I want Thai food or " \
                    "gastropub near University of Washington, or I'm hungry for pizza near me."
    should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def get_help_response(session):
    """help for the user"""
    session_attributes = {}
    card_title = "Things to try saying: French food, brunch place near me"
    speech_output = "Try to set a cuisine type or a location. Something like, French food, or brunch place near me."
    reprompt_text = "Sorry maybe that didn't make sense. You can say, my zipcode is, or, Id like X food."
    should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def prompt_for_defaults():
    """prompt user for default settings"""
    session_attributes = {}
    card_title = "Welcome"
    speech_output = "Welcome to Mos Eisley Cantina. Looks like you're new. Let's set some default " \
                    "locations for looking up restaurants in future. You can set home and or " \
                    "work, by address, zip, or both."
    reprompt_text = "Sorry I didn't get that. Say: home address, work address," \
                    "home zip, or work zip."
    should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def handle_session_end_request(session):
    # end the session and save the user info to the database
    card_title = "Session Ended"
    speech_output = "Thank you for trying the Mos Eisley cantina. We hope you enjoy your meal. Be sure to tell us what " \
                    "you've thought of it next time we chat! " \
                    "Have a nice day! "
    # Setting this to true ends the session and exits the skill.
    should_end_session = True

    item = make_user_previous_recommendation_item(session)
    print('write to the dynamo db')
    print(item)
    print(previous_recs.put_item(Item=item))
    print('successfully write out')
    return build_response(session['attributes'], build_speechlet_response(
        card_title, speech_output, None, should_end_session))


def build_output(session_attributes, card_title, should_end_session):
    """
    Depending on the session_attributes to build the output response
    :param session_attributes:
    :param card_title:
    :param should_end_session:
    :return:
    """
    print(session_attributes)
    if 'SetConstraint' == session_attributes['state']:
        lack = check_constraints(session_attributes)
        # check info is sufficient or not
        if len(lack) == 0:
            # if constraints is sufficient, provide restaurant
            return offer_recommendation(session_attributes, card_title, should_end_session)
        else:
            # if not sufficient, ask user to provide other info
            return prompt_constraint(session_attributes, lack, card_title, should_end_session)

    if 'ChangeRecommendation' == session_attributes['state']:
        return offer_recommendation(session_attributes, card_title, should_end_session)

    if 'SetDefaults' == session_attributes['state']:
        which = ''
        reprompt = ''
        if session_attributes.get('which_zip'):
            which += session_attributes['which_zip'] + ' zipcode '
        if session_attributes.get('which_address'):
            which += session_attributes['which_address'] + ' address '
        if 'home' in which and 'work' in which:
            # TODO: use the address for navigation
            reprompt += 'Would you like to use your home address to search for restaurant?'
            session_attributes['asked'] = 'set_home_address'
        elif 'home' in which:
            reprompt += 'You can tell me your work addresss or zip.'
        else:
            reprompt += 'You can tell me your home addresss or zip.'
        # print('jeenkies! ', get_item_by_key(user_info, session_attributes['this_user_id'], session_attributes['which_zip'] ))
        speech_output = "Okay, {} set. ".format(which)
        speech_output += reprompt

    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt, should_end_session))


def prompt_constraint(session_attributes, lack, card_title, should_end_session):
    """
    randomly pick one un-provided constraint to the user
    TODO: Add more random response sentence
    :param session_attributes:
    :param lack:
    :param card_title:
    :param should_end_session:
    :return:
    """
    prompts = {
        'location': "Where would you like me to look? You can tell me the 5 digit zipcode or your address.",
        'food': "Which cuisine would you like? You can tell me your favorite food."
    }
    reprompts = {
        'location': "Sorry I must've been in another galaxy. Try saying something like, my zipcode is, or just, " \
                    "in WA 98105.",
        'food': "Sorry I'm a space case. Try saying something like 'Ethiopian food' or 'I want to try a beer bar'."
    }
    key = random.randint(0, len(lack) - 1)
    speech_output = prompts[lack[key]]
    speech_reprompt = reprompts[lack[key]]

    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, speech_reprompt, should_end_session))


def offer_recommendation(session_attributes, card_title, should_end_session):
    """
    The output speech for offer restaurants
    TODO: Add more random response with restaurant name
    :param session_attributes:
    :param card_title:
    :param should_end_session:
    :return:
    """
    # check for no API result case
    if session_attributes['no_api_result'] == True:
        speech_output = 'Could you please specify the address or the cuisine you want us looking for? '
        return build_response(session_attributes, build_speechlet_response(
            card_title, speech_output, speech_output, should_end_session))

    restaurant = session_attributes['restaurant']
    name = restaurant['name']
    rating = restaurant['rating']
    review_count = restaurant['review_count']
    price = restaurant['price']

    # TODO: add more
    output_sample = ["How about {}? They have {} stars from {} reviews.".format(name, rating, review_count),
                    "I find a place called {}. They have {} stars from {} reviews.".format(name, rating, review_count),
                    "{} maybe a great choice for you. They have {} stars from {} reviews.".format(name, rating, review_count),
                    "{} serves great food. They have {} stars from {} reviews.".format(name, rating, review_count)]

    # Randomly pick one from output_sample for speech output
    speech_output = output_sample[random.randint(0, len(output_sample) - 1)]
    if price == 1:
        speech_output = speech_output + " And they have a very cheap price. "
        if random.randint(0, 1) == 0:
            speech_output = speech_output + "You can ask me to find a fancy one or ask me for more information about this place."
        else:
            speech_output = speech_output + "How do you like it? You can also ask me for more information about this place."
    elif price == 2:
        speech_output = speech_output + " And they have a moderate price. "
        if random.randint(0, 1) == 0:
            speech_output = speech_output + "You can ask me to find a fancy one or ask me for more information about this place."
        else:
            speech_output = speech_output + "How do you like it? You can also ask me for more information about this place."
    elif price == 3:
        speech_output = speech_output + " But their price is a little bit expensive. "
        if random.randint(0, 1) == 0:
            speech_output = speech_output + "You can ask me to find a cheaper one or ask more information about this place."
        else:
            speech_output = speech_output + "How do you like it? You can also ask me for more information about this place."
    elif price == 4:
        speech_output = speech_output + " But their price is expensive. "
        if random.randint(0, 1) == 0:
            speech_output = speech_output + "You can ask me to find a cheaper one or ask more information about this place."
        else:
            speech_output = speech_output + "How do you like it? You can also ask me for more information about this place."

    if 'previous_rank' in session_attributes and session_attributes['rank'] in session_attributes['previous_rank']:
        speech_output = 'What else do you want to know about {}?'.format(name)

    speech_reprompt = "Sorry I didn't quite get that. Do you want more information about this place? You say that you "\
    "want the phone number, the opening hours, the address, the distance, or the reviews."

    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, speech_reprompt, should_end_session))


def time_helper(time):
    """
    Sample: 2300 -> 11:00 pm
    """
    if int(time[0:2]) < 12:
        return "{}:{} am".format(time[0:2], time[2:4])
    else:
        return "{}:{} pm".format(str(int(time[0:2]) - 12), time[2:4])


def offer_more_data(session_attributes, card_title, should_end_session, data_type):
    """
    The output speech for offer more data
    :param session_attributes:
    :param card_title:
    :param should_end_session:
    :return:
    """

    # id for business detail, used for hour and review search.
    _id = session_attributes['restaurant']['id']
    restaurant = session_attributes['restaurant']

    if card_title == 'RequestMoreData':
        if "phone" in data_type and data_type["phone"].get('value'):
            phone = restaurant['display_phone']
            speech_output = "Their phone number is {}.".format(phone)

            if not session_attributes['restaurant']['phone_asked']:
                speech_output = speech_output + " I can say that again if you want to reserve a table." \
                " Or you can also ask for more information."
                session_attributes['restaurant']['phone_asked'] = True
            else:
                speech_output = speech_output + " What else do you need for this place?"

        elif "address" in data_type and data_type["address"].get('value'):
            address = restaurant['display_address']
            speech_output = "Their address is {}.".format(address)

            if not session_attributes['restaurant']['address_asked']:
                speech_output = speech_output + " You can also ask something like how far is this place."
                session_attributes['restaurant']['phone_asked'] = True
            else:
                speech_output = speech_output + " What else do you need for this place?"

        elif "hours" in data_type and data_type["hours"].get('value'):
            restaurant = search_yelp_business(_id)
            start_time = restaurant['hours'][0]['open'][tm_wday]['start']
            end_time = restaurant['hours'][0]['open'][tm_wday]['end']
            is_open_now = restaurant['hours'][0]['is_open_now']
            if is_open_now:
                speech_output = "This place open now and will close at {}.".format(time_helper(end_time))
            else:
                speech_output = "This place is close now. They open today from {} to {}. " \
                "Or you can say something like I want Chinese food open now to search for restaurant".format(time_helper(start_time), time_helper(end_time))

        # Yelp api only provide text excerpt.
        elif "review" in data_type and data_type["review"].get('value'):
            restaurant = search_yelp_business(_id + '/reviews')
            review_id = session_attributes['restaurant']['review_id']
            name = restaurant['reviews'][review_id]['user']['name'].split(' ')[0]
            rating = restaurant['reviews'][review_id]['rating']
            review = restaurant['reviews'][review_id]['text']
            review = review.strip('.')
            review = review[:max(review.rfind('.'), review.rfind('！'))]
            speech_output = "{} gave {} star and said {}.".format(name, rating, review)
            if rating < 4:
                speech_output = speech_output + " The rating of this reviewer is not so good. " \
                "You can simply say next so that we can give you another recommendation."
            else:
                speech_output = speech_output + " How do you like this place? " \
                "You can also say next so that we can give you another recommendation."
            session_attributes['restaurant']['review_id'] = (review_id + 1) % restaurant['total']

    elif card_title == 'TransportationIntent':
        walking_distance = restaurant['walking_distance']['text']
        walking_duration = restaurant['walking_duration']['text']
        transit_distance = restaurant['transit_distance']['text']
        transit_duration = restaurant['transit_duration']['text']
        driving_distance = restaurant['driving_distance']['text']
        driving_duration = restaurant['driving_duration']['text']

        if "foot" in data_type and data_type["foot"].get('value'):
            speech_output = "It is {} away and it takes {} to walk there.".format(walking_distance, walking_duration)
            if restaurant['walking_distance']['value'] < 30 * 60:
                speech_output = speech_output + " And it is not a long walk. What else do you need for this place?"
            else:
                speech_output = speech_output + " This place is pretty far away. You can ask me how long by bus or by driving."

        elif "bus" in data_type and data_type["bus"].get('value'):
            speech_output = "It is {} away and it takes {} by public transportation.".format(transit_distance, transit_duration)
            if restaurant['walking_distance']['value'] < 60 * 60:
                speech_output = speech_output + " What else do you need for this place?"
            else:
                speech_output = speech_output + " This place is pretty far away. You can ask me how long by driving."

        elif "car" in data_type and data_type["car"].get('value'):
            speech_output = "It is {} away and it takes {} to drive there.".format(driving_distance, driving_duration)
            speech_output = speech_output + " What else do you need for this place?"

        # if not specified, walking time shorter than half an hour: walking + driving, else transit + driving
        elif restaurant['walking_distance']['value'] < 60 * 60:
            speech_output = "It is {} away and it takes {} to walk there or {} to drive there.".format(walking_distance, walking_duration, driving_duration)
        elif restaurant['walking_distance']['value'] < 24 * 60 * 60:
            speech_output = "It is {} away and it takes {} by public transportation or {} to drive there.".format(walking_distance, transit_duration, driving_duration)
        else:
            speech_output = "It seems this place is really far away from your current place. Can you confirm the place where you want me to look?"

    speech_reprompt = "Sorry I didn't get that. What would you like? Try saying something like what is their phone number?"
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, speech_reprompt, should_end_session))


def end_session(session_attributes, card_title, should_end_session=True):
    """
    The output speech for ending the session
    :param session_attributes:
    :param card_title:
    :param should_end_session:
    :return:
    """
    speech_output = 'Thank you for using Mos Eisley Santina. We hope you enjoy your meal, and be sure to let us know ' \
                    ' what you think next time we chat! Have a nice day.'
    item = make_user_previous_recommendation_item(session_attributes)
    print('write to the dynamo db')
    print(item)
    print(previous_recs.put_item(Item=item))
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, speech_output, should_end_session))


def check_constraints(session_attributes):
    """
    check the constraints' sufficiency to call yelp API
    if the constraints is sufficiency, call yelp to generate the restaurant
    if not sufficient, produce the constraints list for the output
    :param session_attributes:
    :return:
    """
    lack = []
    parameters = {}
    for key in require_constraints:
        if key in session_attributes:
            parameters[key] = session_attributes[key]
        else:
            lack.append(key)
    if len(lack) == 0:
        # handle error in google navigation
        try:
            search_with_parameter(session_attributes)
        except:
            session_attributes.pop('location')
            lack.append('location')
    return lack


def search_with_parameter(session_attributes, rank=0):
    """
    call the Yelp API with the parameter dict
    TODO: add more parameter mapping to call YELP API(add more search constraints)
    TODO: not hard-coded
    :param session_attributes:
    :param parameters: parameter dict
    :return:
    """
    cuisine = session_attributes['food']
    location = session_attributes['location']
    now = session_attributes['now'] if 'now' in session_attributes else False
    price = session_attributes['price'] if 'price' in session_attributes else '1, 2, 3, 4'
    places = search_yelp(keyword=cuisine, location=location, open_now=now, price=price, limit=rank + 1)
    # handle API no search result.
    if len(places) == 0:
        session_attributes['no_api_result'] = True
        return
    else:
        session_attributes['no_api_result'] = False
    restaurant = places[len(places) - 1]
    print(restaurant['name'])

    destination = restaurant['location']['display_address'][0] + restaurant['location']['display_address'][1]
    walking_direction = get_google_direction('walking', location, destination)
    transit_direction = get_google_direction('transit', location, destination)
    driving_direction = get_google_direction('driving', location, destination)
    restaurant['walking_distance'] = walking_direction['distance']
    restaurant['walking_duration'] = walking_direction['duration']
    restaurant['transit_distance'] = transit_direction['distance']
    restaurant['transit_duration'] = transit_direction['duration']
    restaurant['driving_distance'] = driving_direction['distance']
    restaurant['driving_duration'] = driving_direction['duration']

    update_restaurant_attributes(session_attributes, restaurant)
    update_rank_attributes(session_attributes, rank)


def update_cuisine_attributes(session_attributes, cuisine):
    session_attributes['food'] = cuisine
    return session_attributes


def update_rank_attributes(session_attributes, rank):
    session_attributes['rank'] = rank
    return session_attributes


def update_location_attributes(session_attributes, location):
    session_attributes["location"] = location
    return session_attributes


def update_restaurant_attributes(session_attributes, restaurant):
    session_attributes['restaurant'] = {}
    session_attributes['restaurant']['name'] = restaurant['name']
    # TODO: dynamo db only support int
    session_attributes['restaurant']['rating'] = int(restaurant['rating'])
    session_attributes['restaurant']['review_count'] = restaurant['review_count']
    session_attributes['restaurant']['review_id'] = 0
    session_attributes['restaurant']['price'] = len(restaurant['price'])
    session_attributes['restaurant']['id'] = restaurant['id']
    session_attributes['restaurant']['display_phone'] = restaurant['display_phone']
    session_attributes['restaurant']['phone_asked'] = False
    session_attributes['restaurant']['display_address'] = restaurant['location']['display_address'][0] + restaurant['location']['display_address'][1]
    session_attributes['restaurant']['address_asked'] = False

    session_attributes['restaurant']['walking_distance'] = restaurant['walking_distance']
    session_attributes['restaurant']['walking_duration'] = restaurant['walking_duration']
    session_attributes['restaurant']['transit_distance'] = restaurant['transit_distance']
    session_attributes['restaurant']['transit_duration'] = restaurant['transit_duration']
    session_attributes['restaurant']['driving_distance'] = restaurant['driving_distance']
    session_attributes['restaurant']['driving_duration'] = restaurant['driving_duration']
    session_attributes['restaurant']['distance_asked'] = False

    return session_attributes


def get_cuisine(session):
    if session.get('attributes', {}) and "food" in session.get('attributes', {}):
        cuisine = session['attributes']['food']
        return cuisine
    else:
        return None


def get_location(session):
    if session.get('attributes', {}) and "location" in session.get('attributes', {}):
        location = session['attributes']['location']
        return location
    else:
        return None


def get_value_from_intent(intent, name):
    if name in intent['slots'] and 'value' in intent['slots'][name]:
        return intent['slots'][name]['value']
    else:
        return None


def get_rank_from_slot(word):
    dict_map = {'first': 0, 'second': 1, 'third': 2, 'forth': 3, 'fifth': 4,
                '1st': 0, '2nd': 1, '3rd': 2, '4th': 3, '5th': 4}
    print(word)
    if word not in dict_map:
        return None
    else:
        return dict_map[word]


def update_session_attribute(session_attributes, key, value):
    """
    Update one attribute of session
    Can check the None value
    :param session_attributes:
    :param key:
    :param value:
    :return:
    """
    if value is None:
        return
    else:
        if key == 'zip':
            key = 'location'
        session_attributes[key] = value
        if key == 'now':
            session_attributes[key] = True
        return


def set_constraint(intent, session):
    """
    Set the constraints of the search
    :param intent:
    :param session:
    :return:
    """
    card_title = intent['name']
    session_attributes = session['attributes']
    should_end_session = False

    if card_title == 'CheapOneIntent':
        price = ''
        for i in range(1, min(2, session_attributes['restaurant']['price'])):
            price = price + ',' + str(i)
        session_attributes['price'] = price.lstrip(',')

    elif card_title == 'FancyOneIntent':
        price = ''
        for i in range(min(4, session_attributes['restaurant']['price'] + 1), 5):
            price = price + ',' + str(i)
        session_attributes['price'] = price.lstrip(',')

    else:
        for key in constraints:
            value = get_value_from_intent(intent, key)
            update_session_attribute(session_attributes, key, value)

    return build_output(session_attributes, card_title, should_end_session)


def request_data(intent, session):
    """
    request data by the user
    TODO: add request data from the new Yelp api
    :param intent:
    :param session:
    :return:
    """
    card_title = intent['name']
    session_attributes = session['attributes']
    should_end_session = False
    data_type = intent['slots']
    return offer_more_data(session_attributes, card_title, should_end_session, data_type)


def change_recommendation(intent, session):
    """
    change recommendation by the user
    TODO: relative index instead of the random one
    TODO: how to provide a list of restaurant for the user to choose? so that user could say fifth one?
    :param intent:
    :param session:
    :return:
    """
    card_title = intent['name']
    session_attributes = session['attributes']
    should_end_session = False
    if 'previous_rank' not in session_attributes:
        session_attributes['previous_rank'] = []
    rank = session_attributes['rank']
    rank_list = session_attributes['previous_rank']
    rank_list.append(rank)
    session_attributes['previous_rank'] = list(set(rank_list))
    if 'next' in intent['slots'] and 'value' in intent['slots']['next']:
        rank = rank + 1
    if 'sequence' in intent['slots'] and 'value' in intent['slots']['sequence']:
        if intent['slots']['sequence']['value'] == 'previous' and rank > 0:
            rank = rank - 1
        else:
            rank = get_rank_from_slot(intent['slots']['sequence']['value'])
            # can't figure the rank
            if rank is None:
                return unsolved_output(intent, session)

    # search with the new rank, it will update the restaurant name and the rank number
    search_with_parameter(session_attributes, rank)

    return build_output(session_attributes, card_title, should_end_session)


def change_constraint(intent, session):
    """
    change constraint by the user
    TODO: change constraints
    :param intent:
    :param session:
    :return:
    """
    card_title = intent['name']
    session_attributes = session['attributes']
    should_end_session = False
    return


def is_positive_feedback(intent):
    """
    check whether is the positive feedback
    :param intent:
    :return:
    """
    if 'positive' in intent['slots'] and 'value' in intent['slots']['positive']:
        return True
    elif 'negative' in intent['slots'] and 'value' in intent['slots']['negative']:
        return False
    else:
        return None


def give_feedback(intent, session):
    """
    record user's feedback for restarting previous conversation or after recommendation
    TODO: change constraints
    :param intent:
    :param session:
    :return:
    """
    card_title = intent['name']
    session_attributes = session['attributes']
    should_end_session = False

    # ask feedback uses the dynamodb info to ask for user feedback of the previous
    if session_attributes['previous_state'] == 'AskFeedback':
        # positive feedback
        if is_positive_feedback(intent):
            # copy the previous session information
            session_attributes['food'] = session_attributes['user_history']['food']
            session_attributes['location'] = session_attributes['user_history']['location']
            session_attributes['rank'] = int(session_attributes['user_history']['rank'])
            rank = session_attributes['rank']
            session_attributes.pop('user_history')
            # search with the new rank, it will update the restaurant name and the rank number
            rank = rank + 1
            print('new search')
            print(session_attributes)
            print(rank)
            search_with_parameter(session_attributes, rank)
            # offer a new recommendation based on previous information
            return offer_recommendation(session_attributes, card_title, should_end_session)
        # negative feedback
        else:
            # ask user for the new food preference and information.
            # TODO: ask user what information to keep. change the recommendations
            session_attributes.pop('user_history')
            session_attributes['state'] = 'initial'
            lack = check_constraints(session_attributes)
            # ask user to provide other info
            return prompt_constraint(session_attributes, lack, card_title, should_end_session)
    # feedback about the recommendation
    else:
        # positive feedback
        if is_positive_feedback(intent):
            # user satisfies with the recommendation
            # end this session and save to dynamodb
            return confirm_exit(session_attributes, card_title, should_end_session)
        # negative feedback
        else:
            # user not satisfied with the recommendation, change another restaurant.
            rank = session_attributes['rank']
            # search with the new rank, it will update the restaurant name and the rank number
            rank = rank + 1
            print('new search')
            print(session_attributes)
            search_with_parameter(session_attributes, rank)
            # offer a new recommendation based on previous information
            return offer_recommendation(session_attributes, card_title, should_end_session)
    return


def thank_you_handler(intent, session):
    '''
    handler for the user said thank you
    :param intent:
    :param session:
    :return:
    '''
    card_title = intent['name']
    session_attributes = session['attributes']
    should_end_session = False
    # when asked questions before, second time when the user said thank you or yes
    if 'asked' in session_attributes:
        if session_attributes['asked'] == 'more_info' or session_attributes['asked'] == 'what_else':
            return handle_session_end_request(session)
        else:
            return confirm_exit(session_attributes, card_title, should_end_session)
    else:
        return confirm_exit(session_attributes, card_title, should_end_session)


def yes_no_handler(intent, session):
    card_title = intent['name']
    session_attributes = session['attributes']
    should_end_session = False
    # when asked questions before, second time when the user said thank you or yes
    print('yes or no handler')
    if 'asked' in session_attributes:
        # Yes/No handler for confirmation of quit
        if session_attributes['asked'] == 'more_info' or session_attributes['asked'] == 'what_else':
            # no to 'Do you want more information'
            if card_title == 'AMAZON.NoIntent':
                return handle_session_end_request(session)
            # Yes to 'Do you want more information'
            else:
                speech_output ='You can ask their phone number, opening hour and distance.'
                return build_response(session_attributes, build_speechlet_response(
                    card_title, speech_output, speech_output, should_end_session))

        # Yes/No handler for set location
        if session_attributes['asked'] == 'set_home_address':
            # no to 'use your home address'
            if card_title == 'AMAZON.NoIntent':
                speech_output = 'Would you like to use your work address to search for restaurant?'
                session_attributes['asked'] = 'set_work_address'
                return build_response(session_attributes, build_speechlet_response(
                    card_title, speech_output, speech_output, should_end_session))
            # Yes to 'use your home address'
            else:
                this_user_id = session["user"]["userId"]
                user_profile = get_item_by_key(user_info, 'user_id', this_user_id)[0]
                session_attributes['location'] = user_profile['home_zip'] if 'home_zip' in user_profile \
                    else user_profile['home_address']
                lack = check_constraints(session_attributes)
                # check info is sufficient or not
                if len(lack) == 0:
                    # if constraints is sufficient, provide restaurant
                    return offer_recommendation(session_attributes, card_title, should_end_session)
                else:
                    # if not sufficient, ask user to provide other info
                    return prompt_constraint(session_attributes, lack, card_title, should_end_session)

        if session_attributes['asked'] == 'set_work_address':
            # Yes to 'use your work address'
            if card_title == 'AMAZON.YesIntent':
                this_user_id = session["user"]["userId"]
                user_profile = get_item_by_key(user_info, 'user_id', this_user_id)[0]
                session_attributes['location'] = user_profile['work_zip'] if 'work_zip' in user_profile \
                    else user_profile['work_address']

            lack = check_constraints(session_attributes)
            # check info is sufficient or not
            if len(lack) == 0:
                # if constraints is sufficient, provide restaurant
                return offer_recommendation(session_attributes, card_title, should_end_session)
            else:
                # if not sufficient, ask user to provide other info
                return prompt_constraint(session_attributes, lack, card_title, should_end_session)

    # not asked question before, treat as the Positive feedback
    else:
        # Positive feedback
        if card_title == 'AMAZON.YesIntent':
            return confirm_exit(session_attributes, card_title, should_end_session)
        # negative feedback
        else:
            # user not satisfied with the recommendation, change another restaurant.
            rank = session_attributes['rank']
            # search with the new rank, it will update the restaurant name and the rank number
            rank = rank + 1
            print('new search')
            print(session_attributes)
            search_with_parameter(session_attributes, rank)
            # offer a new recommendation based on previous information
            return offer_recommendation(session_attributes, card_title, should_end_session)


def confirm_exit(session_attributes, card_title, should_end_session):
    random_int = random.randint(0, 1)
    if random_int == 0:
        speech_output = 'What else can I do for you?'
        session_attributes['asked'] = 'what_else'
    else:
        speech_output = 'Do you want more information?'
        session_attributes['asked'] = 'more_info'
    reprompt_output = 'You can ask their phone number, opening hour and distance.'
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_output, should_end_session))


def unsolved_output(intent, session):
    """
    For unsolved state or input, prompt all the current attributes
    TODO: add more reprompt according to the previous state info
    :param intent:
    :param session:
    :return:
    """
    card_title = intent['name']
    session_attributes = session['attributes']
    should_end_session = False
    speech_output = ""
    if 'location' in session_attributes:
        speech_output += "I now know your location is " + \
                        session_attributes['location'] + ". "
    if 'cuisine' in session_attributes:
        speech_output += "I now know your favorite cuisine is " + \
                        session_attributes['cuisine'] + ". "
    else:
        speech_output = "I'm not sure what your favorite cuisine is. " \
                        "Please try again."
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, speech_output, should_end_session))


# --------------- Events ------------------
# intent handler register
# adding your intent handler function name to her when you want to add your new intent
intent_handler = {
    'SetConstraint': set_constraint,
    'CheapOneIntent': set_constraint,
    'FancyOneIntent': set_constraint,
    'RequestMoreData': request_data,
    'TransportationIntent': request_data,
    'ChangeRecommendation': change_recommendation,
    'ChangeConstraint': change_constraint,
    'GiveFeedback': give_feedback,
    'Unsolved': unsolved_output,
    'ThankYou': thank_you_handler,
    'AMAZON.YesIntent': yes_no_handler,
    'AMAZON.NoIntent': yes_no_handler,
    'SetDefaults': set_default_zip_or_address
}

# shared state, these intent corresponding to same state to constraint state space
# these shared the GiveFeedback state.
shared_state = ['ThankYou', 'AMAZON.YesIntent', 'AMAZON.NoIntent']

# global variables for the constraints
constraints = ['food', 'location', 'zip', 'now', 'price']
# global variables for the required constraints used in prompt_constraint function
# will add more in the future
require_constraints = ['food', 'location']


previous_state = {
    'SetConstraint': {'initial', 'SetConstraint', 'SetDefaults', 'GiveFeedback'},
    'RequestMoreData': {'SetConstraint', 'ChangeRecommendation', 'RequestMoreData', 'GiveFeedback'},
    'ChangeRecommendation': {'SetConstraint', 'RequestMoreData', 'ChangeRecommendation', 'GiveFeedback'},
    'ChangeConstraint': {'SetConstraint', 'RequestMoreData', 'ChangeRecommendation', 'ChangeConstraint'},
    'GiveFeedback': {'AskFeedback', 'SetConstraint', 'RequestMoreData', 'ChangeRecommendation', 'ChangeConstraint', 'GiveFeedback', 'SetDefaults'},
    'SetDefaults': {'initial', 'SetDefaults'},
}


def check_previous_state(session):
    """
    check the
    :param session:
    :return: boolean
    """
    previous = session['attributes']['previous_state']
    current = session['attributes']['state']
    if previous in previous_state[current]:
        return True
    else:
        return False


def on_session_started(session_started_request, session):
    """ Called when the session starts """

    print("on_session_started requestId=" + session_started_request['requestId']
          + ", sessionId=" + session['sessionId'])


def on_launch(launch_request, session):
    """ Called when the user launches the skill without specifying what they
    want

    two kinds of responses, randomly pick, ask user for feedback
    """

    print("on_launch requestId=" + launch_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # check whether first time user
    # if you want to pretend you're unrecognised for testing make 'this_user_id' into a bogus value like 'abcdef'
    this_user_id = session["user"]["userId"]
    user_history = get_item_by_key(previous_recs, 'user_id', this_user_id)
    user_profile = get_item_by_key(user_info, 'user_id', this_user_id)
    print(user_history)
    if not user_profile:
        # if you want to add thing to the DB do it this way:
        # user_info.put_item(Item=make_user_info_item(this_user_id))
        user_info.put_item(Item={'user_id': this_user_id})
        return prompt_for_defaults()
    elif not user_history:
        return prompt_for_defaults()
    else:
        # return get_welcome_back_response()
        # Dispatch to your skill's launch
        # TODO: if the user exist in the database, we need to update information
        # like user_info.put_item(Item={'user_id':this_user_id})
        print('read from the database')
        # should be (0,1), 50% likely to use the history. For test, set to 100%
        random_int = random.randint(0, 1)
        if random_int == 0:
            # set the newest history
            return ask_for_feedback(session, user_history[-1])
        else:
            return get_welcome_response()


def ask_for_feedback(session, user_history):
    if 'attributes' not in session:
        session['attributes'] = {}
        session['attributes']['state'] = 'AskFeedback'
    session['attributes']['previous_state'] = session['attributes']['state']
    session['attributes']['state'] = 'AskFeedback'
    session['attributes']['user_history'] = user_history
    card_title = "Welcome"
    print(user_history)
    speech_output = "Welcome back to Mos Eisley Cantina. How do you like our last recommendation "
    # TODO: change the previous constraints
    if 'restaurant' in user_history:
        speech_output += 'of ' + user_history['restaurant']['name'] + ' ?'
    reprompt_text = "Sorry I didn't get that. You can offer us your feedback so we get to know you better in future."
    should_end_session = False
    return build_response(session['attributes'], build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def on_session_ended(session_ended_request, session):
    """ Called when the user ends the session.
    Is not called when the skill returns should_end_session=true
    """
    print("on_session_ended requestId=" + session_ended_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # add cleanup logic here


def state_manager(intent, session):
    """
    Add the state change logic here
    will add more logics here
    :param intent:
    :param session:
    :return:
    """
    if 'attributes' not in session:
        session['attributes'] = {}
        session['attributes']['state'] = 'initial'
    session['attributes']['previous_state'] = session['attributes']['state']
    session['attributes']['state'] = intent['name']

    if intent['name'] in shared_state:
        session['attributes']['state'] = 'GiveFeedback'
    elif intent['name'] == 'TransportationIntent':
        session['attributes']['state'] = 'RequestMoreData'
    elif intent['name'] == 'CheapOneIntent':
        session['attributes']['state'] = 'SetConstraint'
    elif intent['name'] == 'FancyOneIntent':
        session['attributes']['state'] = 'SetConstraint'

    if check_previous_state(session):
        return intent_handler[intent['name']](intent, session)
    else:
        # not update the current state, roll back to the previous state
        session['attributes']['state'] = session['attributes']['previous_state']
        return intent_handler['Unsolved'](intent, session)


def on_intent(intent_request, session):
    """ Called when the user specifies an intent for this skill """
    """ State Control Manager """

    print("on_intent requestId=" + intent_request['requestId'] +
          ", sessionId=" + session['sessionId'])

    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']
    print(intent_name)
    # Dispatch to your skill's intent handlers
    if intent_name in intent_handler:
        # for the registered and our defined intent
        return state_manager(intent, session)
    elif intent_name == "AMAZON.HelpIntent":
        return get_help_response(session)
    elif intent_name == "AMAZON.CancelIntent" or intent_name == "AMAZON.StopIntent":
        return handle_session_end_request(session)
    #elif intent_name == "AMAZON.YesIntent":
    #elif intent_name == "AMAZON.NoIntent"
    else:
        raise ValueError("Invalid intent")



# --------------- Main handler ------------------

def lambda_handler(event, context):
    """ Route the incoming request based on type (LaunchRequest, IntentRequest,
    etc.) The JSON body of the request is provided in the event parameter.
    """
    print("event.session.application.applicationId=" +
          event['session']['application']['applicationId'])

    """
    Uncomment this if statement and populate with your skill's application ID to
    prevent someone else from configuring a skill that sends requests to this
    function.
    """
    # if (event['session']['application']['applicationId'] !=
    #         "amzn1.echo-sdk-ams.app.[unique-value-here]"):
    #     raise ValueError("Invalid Application ID")

    if event['session']['new']:
        on_session_started({'requestId': event['request']['requestId']},
                           event['session'])

    if event['request']['type'] == "LaunchRequest":
        return on_launch(event['request'], event['session'])
    elif event['request']['type'] == "IntentRequest":
        return on_intent(event['request'], event['session'])
    elif event['request']['type'] == "SessionEndedRequest":
        return on_session_ended(event['request'], event['session'])
    return logging.debug()
