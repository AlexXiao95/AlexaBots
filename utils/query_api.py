from botocore.vendored import requests

# API Keys (linked to my personal google and yelp accounts)
# Maximum number of queries per day: 5000
GOOGLE_KEY = 'ADD YOUR GOOGLE_KEY HERE'
YELP_KEY = 'ADD YOUR YELP_KEY HERE'

# API urls
GOOGLE_NEARBYSEARCH_PATH = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json'
GOOGLE_TEXTSEARCH_PATH = 'https://maps.googleapis.com/maps/api/place/textsearch/json'
GOOGLE_DETAIL_PATH = 'https://maps.googleapis.com/maps/api/place/details/json'

GOOGLE_DIRECTION_PATH = 'https://maps.googleapis.com/maps/api/directions/json'

YELP_SEARCH_PATH = 'https://api.yelp.com/v3/businesses/search'
YELP_BUSINESS_PATH = 'https://api.yelp.com/v3/businesses/'  # Business ID will come after slash.


# --------------------------------- GOOGLE ---------------------------------- #
def search_google(keyword, location='', radius=8000, types=['restaurant',], limit=1, api_key=GOOGLE_KEY):
    """Query the Google Search API by a search keyword and location
            Args:
                keyword: [str] You can put food type and location here
                location: [str] The latitude/longitude, e.g. '47.606210, -122.332070' (leave it blank if you don't have this)
                radius: [str] The distance constraint given the location(latitude/longitude)
                types: [list of str] the type of business we are going to search (the default value is 'restaurant')
                limit: [int] number of items in query result
                api_key: [str] KEY for api query (the default value should work)
            Returns:
                places: A list of restaurants information (in JSON format).
                    formatted_address: [str] address in [Street No., City, State Zipcode, Country] format
                    geometry: [dict] location(latitude, longitude), viewport: (not sure what is this for)
                    icon: [str] a url to the restaurant's icon
                    name: [str]
                    opening_hours: [dict] open_now[boolean], weekday_text
                    photos: [list] urls for photos
                    place_id [str]: used for detail information (get_google_detail())
                    id: [str] (not sure, ignore it for now)
                    price_level: [int] 1-5, the larger this number is, the more expensive
                    rating: [double] 0-5, the larger this number is, the better
                    reference: [str] (not sure what is this for)
                    types [list] categories this restaurant belongs to
                    detail (information of this attribute is in the function get_google_detail)
    """
    url_params = {
        'query': keyword.replace(' ', '+'),
        'types': types,
        'key': api_key
    }
    if location != '':
        url_params['location'] = location.replace(' ', '+')
        url_params['radius'] = radius

    g_places = request(GOOGLE_TEXTSEARCH_PATH, api_key, url_params=url_params)
    places = g_places['results'][:limit]
    # for i in range(len(places)):
    #     detail = get_google_detail(places[i]['place_id'])
    #     places[i]['detail'] = detail
    return places


def get_google_detail(placeid, api_key=GOOGLE_KEY):
    """Get the detail information for a Google Place
                Args:
                    placeid: [str] place_id get from search_google, to retrieval a specific restaurant
                    api_key: [str]
                Returns:
                    detail: The JSON response for place detail information
                        address_components: [dict] JSON format address
                        adr_address: [str] a xml format address
                        formatted_address: [str]
                        formatted_phone_number: [str] (206) 557-7532
                        geometry: [dict] location(latitude, longitude), viewport
                        icon [str]: a url to the icon of the restaurant
                        international_phone_number: [str] phone number with international area code as prefix
                        name: [str]
                        opening_hours: [dict] open_now[boolean], periods(close, open)
                        reviews: [list] reviews together with the author information
                        photos: [list] several urls for photos
                        place_id: [str] id to retrieval the restaurant
                        id: [str] (not sure, ignore it for now)
                        vicinity: [str] name of the area
                        price_level
                        rating
                        reference
                        scope
                        types
                        url
                        utc_offset
                        website

    """
    url_params = {
        'placeid': placeid.replace(' ', '+'),
        'key': api_key
    }
    detail = request(GOOGLE_DETAIL_PATH, api_key, url_params=url_params)
    return detail['result']


def get_google_direction(travelmode, origin, destination, use_id=False, api_key=GOOGLE_KEY):
    """Query the Google Direction API for travel summary
            Args:
                travelmode: [string]
                origin: [string]
                destination: [string]
                use_id: [boolean] True for using place_id for origin and destination
                api_key: [string]
            Returns:
                direction: The JSON response for travel summary.
    """

    if use_id:
        origin = 'place_id:%s' % origin
        destination = 'place_id:%s' % destination
    url_params = {
        'origin': origin,
        'destination': destination,
        'key': api_key,
        'mode': travelmode,
        'avoid': []
    }

    direction = request(GOOGLE_DIRECTION_PATH, api_key, url_params=url_params)
    return direction['routes'][0]['legs'][0]


# --------------------------------- YELP ---------------------------------- #
def search_yelp(keyword, location, api_key=YELP_KEY, limit=1, price=None, open_at=None, open_now=False, radius=8000):
    """Query the YELP Search API by a search term and location.
    Args:
        term: [str] The search term passed to the API.
        location: [str] The search location passed to the API.
        open_at: [int] The time-value passed to the API. Cannot be set in conjunction with open_now; if it is, function defaults to open_now.
        open_now: [bool] The bool val passed to the API. Cannot be set in conjunction with open_at; if it is, function defaults to open_now.
    Returns:
        dict: The JSON response from the request.
            id: [str]
            alias: [str]
            name: [str]
            image_url: [str]
            is_closed: [bool]
            url: [str]
            review_count: [int]
            categories: [list]
            rating: [double]
            coordinates: [dict] latitude & longitude
            price: [str]  several '$'s
            location: [dict] formatted
            phone: [str]
            display_phone: [str]
            distance [double]
    """

    try:
        assert not(open_at and open_now)
    except:
        open_at = None
        open_now = True

    url_params = {
        'term': keyword.replace(' ', '+'),
        'location': location.replace(' ', '+'),
        'limit': limit,
        'radius': radius
    }

    if open_now:
        url_params['open_now'] = True
    elif open_at:
        url_params['open_at'] = open_at

    if price:
        url_params['price'] = price

    places = request(YELP_SEARCH_PATH, api_key, url_params=url_params)
    return places['businesses']


def search_yelp_business(business_id, api_key=YELP_KEY):
    """Query the YELP Business API by a business ID. (This is currently not used in our project)
    Args:
        business_id (str): The ID of the business to query.
    Returns:
        dict: The JSON response from the request.
    """
    path = YELP_BUSINESS_PATH + business_id

    return request(path, api_key)


# --------------------------------- URL wrapper ---------------------------------- #
def request(path, api_key, url_params=None):
    """Given your GOOGLE/YELP API_KEY, send a GET request to the API.
    Args:
        host (str): The domain host of the API.
        path (str): The path of the API after the domain.
        API_KEY (str): Your API Key.
        url_params (dict): An optional set of query parameters in the request.
    Returns:
        dict: The JSON response from the request.
    Raises:
        HTTPError: An error occurs from the HTTP request.
    """
    url_params = url_params or {}
    headers = {'Authorization': 'Bearer %s' % api_key,}

    print('Querying {0} ...'.format(path))

    response = requests.request('GET', path, headers=headers, params=url_params)
    return response.json()


if __name__ == '__main__':
    google_places = search_google(keyword='Seattle seafood', location='47.606210, -122.332070', radius='8000')  # location='47.606210, -122.332070', radius=8000
    yelp_places = search_yelp(keyword='seafood', location='Seattle', price='3', limit=10, radius=5000)
    direction = get_google_direction('driving', 'Seattle', 'Portland')

    print('Direction: \n', direction)
    print('Google: \n', google_places[0])
    print('\nYelp: \n', yelp_places[0])
    
    yelp_places = search_yelp_business('NCDpIDp2f-DhPO5sL5Hbdw')
    print('\nYelp: \n', yelp_places['hours'][0]['open'][1])