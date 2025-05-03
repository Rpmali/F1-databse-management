from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import google.oauth2.id_token
from google.auth.transport import requests
from google.cloud import firestore, storage
import starlette.status as status
import logging
import os

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI()

# Check if credentials file exists and is readable
credentials_path = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
if not credentials_path:
    logger.error("GOOGLE_APPLICATION_CREDENTIALS environment variable not set")
    raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS environment variable not set")
if not os.path.exists(credentials_path):
    logger.error(f"Credentials file not found at {credentials_path}")
    raise RuntimeError(f"Credentials file not found at {credentials_path}")
logger.info(f"Using credentials file at {credentials_path}")

try:
    # Initialize Firestore client
    firestore_db = firestore.Client()
    # Test the connection by making a simple query
    test_query = firestore_db.collection('drivers').limit(1).get()
    list(test_query)  # Force the query to execute
    logger.info("Successfully connected to Firestore and verified connection")
except Exception as e:
    logger.error(f"Failed to initialize Firestore: {str(e)}")
    raise

firebase_request_adapter = requests.Request()

app.mount('/static', StaticFiles(directory='static'), name='static')
templates = Jinja2Templates(directory="templates")


def getUser(user_token):
    user = firestore_db.collection('user').document(user_token['user_id'])
    return user


def validateFirebaseToken(id_token):
    if not id_token:
        return None
    user_token = None
    try:
        user_token = google.oauth2.id_token.verify_firebase_token(
            id_token, firebase_request_adapter)
    except ValueError as err:
        print(str(err))
    return user_token


def require_authentication(user_token):
    if not user_token:
        raise HTTPException(
            status_code=401, detail="You must be logged in to perform this action.")


@app.get('/')
async def root(request: Request):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)

    return RedirectResponse(url='/dashboard', status_code=status.HTTP_302_FOUND)


@app.get('/login')
async def login(request: Request):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)

    if not user_token:
        return templates.TemplateResponse('login.html', {'request': request})

    return RedirectResponse(url='/dashboard', status_code=status.HTTP_302_FOUND)


@app.get('/dashboard')
async def dashboard(request: Request):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)

    return templates.TemplateResponse('dashboard.html', {
        'request': request,
        'user_token': user_token
    })


@app.get('/add-driver')
async def add_driver_form(request: Request):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    if not user_token:
        return templates.TemplateResponse('dashboard.html', {
            'request': request,
            'error_message': 'Please log in first to add a driver.'
        })
    user = getUser(user_token)

    teams = firestore_db.collection('teams').get()

    return templates.TemplateResponse('add_driver.html', {
        'request': request,
        'user_token': user_token,
        'teams': teams,
        'user': user
    })


@app.post('/add-driver')
async def add_driver(request: Request):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    if not user_token:
        return templates.TemplateResponse('dashboard.html', {
            'request': request,
            'error_message': 'Please log in first to add a driver.'
        })
        
    require_authentication(user_token)

    user = getUser(user_token)

    teams = firestore_db.collection('teams').get()

    form_data = await request.form()
    driver_name = form_data.get('driver_name')
    driver_age = form_data.get('driver_age')
    team_name = form_data.get('team_name')
    total_pole_positions = form_data.get('total_pole_positions')
    total_race_wins = form_data.get('total_race_wins')
    total_points_scored = form_data.get('total_points_scored')
    total_world_titles = form_data.get('total_world_titles')
    total_fastest_laps = form_data.get('total_fastest_laps')

    driver_data = {
        'name': driver_name,
        'age': int(driver_age),
        'team': team_name,
        'total_pole_positions': int(total_pole_positions),
        'total_race_wins': int(total_race_wins),
        'total_points_scored': int(total_points_scored),
        'total_world_titles': int(total_world_titles),
        'total_fastest_laps': int(total_fastest_laps)
    }

    drivers = firestore_db.collection('drivers').get()
    if driver_name in [driver.to_dict()['name'] for driver in drivers]:
        error_message = "Driver already exists."
        return templates.TemplateResponse('add_driver.html', {
            'request': request,
            'user_token': user_token,
            'error_message': error_message,
            'teams': teams,
            'user': user
        })

    firestore_db.collection('drivers').add(driver_data)

    success_message = "Driver added successfully."
    return templates.TemplateResponse('add_driver.html', {
        'request': request,
        'user_token': user_token,
        'success_message': success_message,
        'teams': teams,
        'user': user
    })


@app.get('/get-drivers')
async def get_drivers(request: Request):
    try:
        logger.debug("Attempting to fetch drivers from Firestore")
        drivers = firestore_db.collection('drivers').get()
        logger.info(f"Successfully fetched {len(list(drivers))} drivers")
        return templates.TemplateResponse('all_drivers.html', {
            'request': request, 
            'drivers': drivers,
            'error_message': None
        })
    except Exception as e:
        logger.error(f"Error fetching drivers: {str(e)}")
        return templates.TemplateResponse('all_drivers.html', {
            'request': request,
            'drivers': [],
            'error_message': "Failed to load drivers. Please try again later."
        })


@app.get('/delete-driver')
async def delete_driver_form(request: Request):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    if not user_token:
        return templates.TemplateResponse('dashboard.html', {
            'request': request,
            'error_message': 'Please log in first to delete a driver.'
        })
    user = getUser(user_token)

    drivers = firestore_db.collection('drivers').get()

    return templates.TemplateResponse('delete_driver.html', {
        'request': request,
        'user_token': user_token,
        'drivers': drivers,
        'user': user
    })


@app.post('/delete-driver')
async def delete_driver(request: Request):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    require_authentication(user_token)

    form_data = await request.form()
    driver_name = form_data.get('driver_name')

    drivers = firestore_db.collection('drivers').get()

    driver_found = False
    for driver in drivers:
        if driver.to_dict()['name'] == driver_name:
            driver.reference.delete()
            driver_found = True
            break

    drivers = firestore_db.collection('drivers').get()

    if not driver_found:
        error_message = "Driver not found."
        return templates.TemplateResponse('delete_driver.html', {
            'request': request,
            'user_token': user_token,
            'error_message': error_message,
            'drivers': drivers
        })

    success_message = "Driver deleted successfully."
    return templates.TemplateResponse('delete_driver.html', {
        'request': request,
        'user_token': user_token,
        'success_message': success_message,
        'drivers': drivers
    })


@app.get('/update-driver')
async def update_driver_form(request: Request):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    if not user_token:
        return templates.TemplateResponse('dashboard.html', {
            'request': request,
            'error_message': 'Please log in first to update a driver.'
        })

    teams = firestore_db.collection('teams').get()
    drivers = firestore_db.collection('drivers').get()

    return templates.TemplateResponse('update_driver.html', {
        'request': request,
        'user_token': user_token,
        'teams': teams,
        'drivers': drivers
    })


@app.post('/update-driver')
async def update_driver(request: Request):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    require_authentication(user_token)

    user = getUser(user_token)

    
    teams = firestore_db.collection('teams').get()
    drivers = firestore_db.collection('drivers').get()

    form_data = await request.form()
    driver_name = form_data.get('driver_name')
    driver_age = form_data.get('driver_age')
    team_name = form_data.get('team')
    total_pole_positions = form_data.get('total_pole_positions')
    total_race_wins = form_data.get('total_race_wins')
    total_points_scored = form_data.get('total_points_scored')
    total_world_titles = form_data.get('total_world_titles')
    total_fastest_laps = form_data.get('total_fastest_laps')

    driver_data = {
        'name': driver_name,
        'age': int(driver_age),
        'team': team_name,
        'total_pole_positions': int(total_pole_positions),
        'total_race_wins': int(total_race_wins),
        'total_points_scored': int(total_points_scored),
        'total_world_titles': int(total_world_titles),
        'total_fastest_laps': int(total_fastest_laps)
    }

    driver_found = False
    for driver in drivers:
        if driver.to_dict()['name'] == driver_name:
            driver.reference.update(driver_data)
            driver_found = True
            break

    drivers = firestore_db.collection('drivers').get()

    if not driver_found:
        error_message = "Driver not found."
        return templates.TemplateResponse('update_driver.html', {
            'request': request,
            'user_token': user_token,
            'error_message': error_message,
            'teams': teams,
            'drivers': drivers,
            'user': user
        })

    success_message = "Driver updated successfully."
    return templates.TemplateResponse('update_driver.html', {
        'request': request,
        'user_token': user_token,
        'success_message': success_message,
        'teams': teams,
        'drivers': drivers,
        'user': user
    })


@app.get('/add-team')
async def add_team_form(request: Request):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    if not user_token:
        return templates.TemplateResponse('dashboard.html', {
            'request': request,
            'error_message': 'Please log in first to add a team.'
        })
    user = getUser(user_token)
    return templates.TemplateResponse('add_team.html', {
        'request': request,
        'user_token': user_token,
        'user': user
    })


@app.post('/add-team')
async def add_team(request: Request):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    if not user_token:
        return templates.TemplateResponse('dashboard.html', {
            'request': request,
            'error_message': 'Please log in first to add a team.'
        })
    require_authentication(user_token)
    user = getUser(user_token)

    form_data = await request.form()
    team_name = form_data.get('team_name')
    year_founded = form_data.get('year_founded')
    total_pole_positions = form_data.get('total_pole_positions')
    total_race_wins = form_data.get('total_race_wins')
    total_constructor_titles = form_data.get('total_constructor_titles')
    finishing_position_in_previous_season = form_data.get(
        'finishing_position_in_previous_season')

    team_data = {
        'name': team_name,
        'year_founded': int(year_founded),
        'total_pole_positions': int(total_pole_positions),
        'total_race_wins': int(total_race_wins),
        'total_constructor_titles': int(total_constructor_titles),
        'finishing_position_in_previous_season': int(finishing_position_in_previous_season)
    }

    teams = firestore_db.collection('teams').get()
    if team_name in [team.to_dict()['name'] for team in teams]:
        error_message = "Team already exists."
        return templates.TemplateResponse('add_team.html', {
            'request': request,
            'user_token': user_token,
            'error_message': error_message,
            'teams': teams,
            'user': user
        })

    firestore_db.collection('teams').add(team_data)

    success_message = "Team added successfully."
    return templates.TemplateResponse('add_team.html', {
        'request': request,
        'success_message': success_message,
        'teams': teams,
        'user': user    
    })


@app.get('/get-teams')
async def get_teams(request: Request):
    teams = firestore_db.collection('teams').get()
    return templates.TemplateResponse('all_teams.html', {'request': request, 'teams': teams})


@app.get('/update-team')
async def update_team_form(request: Request):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    if not user_token:
        return templates.TemplateResponse('dashboard.html', {
            'request': request,
            'error_message': 'Please log in first to update a team.'
        })
    user = getUser(user_token)

    teams = firestore_db.collection('teams').get()

    return templates.TemplateResponse('update_team.html', {
        'request': request,
        'user_token': user_token,
        'teams': teams,
        'user': user
    })


@app.post('/update-team')
async def update_team(request: Request):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    require_authentication(user_token)

    user = getUser(user_token)

    teams = firestore_db.collection('teams').get()

    form_data = await request.form()
    team_name = form_data.get('team_name')
    year_founded = form_data.get('year_founded')
    total_pole_positions = form_data.get('total_pole_positions')
    total_race_wins = form_data.get('total_race_wins')
    total_constructor_titles = form_data.get('total_constructor_titles')
    finishing_position_in_previous_season = form_data.get(
        'finishing_position_in_previous_season')

    team_data = {
        'name': team_name,
        'year_founded': int(year_founded),
        'total_pole_positions': int(total_pole_positions),
        'total_race_wins': int(total_race_wins),
        'total_constructor_titles': int(total_constructor_titles),
        'finishing_position_in_previous_season': int(finishing_position_in_previous_season)
    }

    team_found = False
    for team in teams:
        if team.to_dict()['name'] == team_name:
            team.reference.update(team_data)
            team_found = True
            break

    teams = firestore_db.collection('teams').get()

    if not team_found:
        error_message = "Team not found."
        return templates.TemplateResponse('update_team.html', {
            'request': request,
            'user_token': user_token,
            'error_message': error_message,
            'teams': teams,
            'user': user
        })

    success_message = "Team updated successfully."
    return templates.TemplateResponse('update_team.html', {
        'request': request,
        'user_token': user_token,
        'success_message': success_message,
        'teams': teams,
        'user': user
    })


@app.get('/all-teams')
async def all_teams(request: Request):
    teams = firestore_db.collection('teams').get()

    return templates.TemplateResponse('all_teams.html', {
        'request': request,
        'teams': teams
    })


@app.get('/delete-team')
async def delete_team_form(request: Request):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    if not user_token:
        return templates.TemplateResponse('dashboard.html', {
            'request': request,
            'error_message': 'Please log in first to delete a team.'
        })
    teams = firestore_db.collection('teams').get()

    return templates.TemplateResponse('delete_team.html', {
        'request': request,
        'teams': teams
    })


@app.post('/delete-team')
async def delete_team(request: Request):
    id_token = request.cookies.get("token")
    user_token = validateFirebaseToken(id_token)
    require_authentication(user_token)

    user = getUser(user_token)

    form_data = await request.form()
    team_name = form_data.get('team_name')

    teams = firestore_db.collection('teams').get()

    team_found = False
    for team in teams:
        if team.to_dict()['name'] == team_name:
            team.reference.delete()
            team_found = True
            break

    teams = firestore_db.collection('teams').get()

    if not team_found:
        error_message = "Team not found."
        return templates.TemplateResponse('delete_team.html', {
            'request': request,
            'user_token': user_token,
            'error_message': error_message,
            'teams': teams,
            'user': user
        })

    success_message = "Team deleted successfully."
    return templates.TemplateResponse('delete_team.html', {
        'request': request,
        'user_token': user_token,
        'success_message': success_message,
        'teams': teams,
        'user': user
    })


@app.get('/query-drivers')
async def query_drivers_form(request: Request):
    return templates.TemplateResponse('query_drivers.html', {
        'request': request
    })


@app.post('/query-drivers')
async def query_drivers(request: Request):

    form_data = await request.form()
    attribute = form_data.get('attribute')
    operator = form_data.get('operator')
    value = form_data.get('value')

    try:
        value = int(value)
    except ValueError:
        return templates.TemplateResponse('query_drivers.html', {
            'request': request,
            'error_message': 'Please enter a valid number for the value'
        })

    drivers = firestore_db.collection('drivers').get()

    matching_drivers = []
    for driver in drivers:
        driver_data = driver.to_dict()
        if attribute in driver_data:
            try:
                driver_value = int(driver_data[attribute])
                if operator == '<' and driver_value < value:
                    matching_drivers.append(driver_data)
                elif operator == '>' and driver_value > value:
                    matching_drivers.append(driver_data)
                elif operator == '==' and driver_value == value:
                    matching_drivers.append(driver_data)
            except (ValueError, TypeError):
                continue

    return templates.TemplateResponse('query_drivers.html', {
        'request': request,
        'drivers': matching_drivers
    })


@app.get('/query-teams')
async def query_teams_form(request: Request):
    return templates.TemplateResponse('query_teams.html', {
        'request': request
    })


@app.post('/query-teams')
async def query_teams(request: Request):

    form_data = await request.form()
    attribute = form_data.get('attribute')
    operator = form_data.get('operator')
    value = form_data.get('value')

    try:
        value = int(value)
    except ValueError:
        return templates.TemplateResponse('query_teams.html', {
            'request': request,
            'error_message': 'Please enter a valid number for the value'
        })
    
    teams = firestore_db.collection('teams').get()

    matching_teams = []
    for team in teams:
        team_data = team.to_dict()
        if attribute in team_data:
            try:
                team_value = int(team_data[attribute])
                if operator == '<' and team_value < value:
                    matching_teams.append(team_data)
                elif operator == '>' and team_value > value:
                    matching_teams.append(team_data)
                elif operator == '==' and team_value == value:
                    matching_teams.append(team_data)
            except (ValueError, TypeError):
                continue

    return templates.TemplateResponse('query_teams.html', {
        'request': request,
        'teams': matching_teams
    })


@app.get('/driver/{driver_id}')
async def driver_detail(request: Request, driver_id: str):
    driver_doc = firestore_db.collection('drivers').document(driver_id).get()
    if not driver_doc.exists:
        raise HTTPException(status_code=404, detail="Driver not found")
    driver = driver_doc.to_dict()
    return templates.TemplateResponse('driver_detail.html', {'request': request, 'driver': driver})


@app.get('/team/{team_id}')
async def team_detail(request: Request, team_id: str):
    team_doc = firestore_db.collection('teams').document(team_id).get()
    if not team_doc.exists:
        raise HTTPException(status_code=404, detail="Team not found")
    team = team_doc.to_dict()
    return templates.TemplateResponse('team_detail.html', {'request': request, 'team': team})


@app.get('/compare-drivers')
async def compare_drivers_form(request: Request):
    drivers = firestore_db.collection('drivers').get()
    driver_list = [{'id': driver.id, 'name': driver.to_dict().get('name')} for driver in drivers]
    
    return templates.TemplateResponse('compare_drivers.html', {
        'request': request,
        'drivers': driver_list,
        'driver1': None,
        'driver2': None
    })

@app.post('/compare-drivers')
async def compare_drivers(request: Request):
    form_data = await request.form()
    driver1_id = form_data.get('driver1')
    driver2_id = form_data.get('driver2')
    drivers = firestore_db.collection('drivers').get()
    
    driver1 = firestore_db.collection('drivers').document(driver1_id).get()
    driver2 = firestore_db.collection('drivers').document(driver2_id).get()
    
    if driver1.exists and driver2.exists:
        driver1_data = driver1.to_dict()
        driver2_data = driver2.to_dict()
        driver_list = [{'id': driver.id, 'name': driver.to_dict().get('name')} for driver in drivers]
        return templates.TemplateResponse('compare_drivers.html', {
            'request': request,
            'driver1': driver1_data,
            'driver2': driver2_data,
            'drivers': driver_list
        })
    else:
        return templates.TemplateResponse('compare_drivers.html', {
            'request': request,
            'error': 'One or both drivers not found.'
        })

@app.get('/compare-teams')
async def compare_teams_form(request: Request):
    teams = firestore_db.collection('teams').get()
    team_list = [{'id': team.id, 'name': team.to_dict().get('name')} for team in teams]  
    return templates.TemplateResponse('compare_teams.html', {
        'request': request,
        'teams': team_list,
        'team1': None,
        'team2': None
    })

@app.post('/compare-teams')
async def compare_teams(request: Request):
    form_data = await request.form()
    team1_id = form_data.get('team1')
    team2_id = form_data.get('team2')
    teams = firestore_db.collection('teams').get()
    
    team1 = firestore_db.collection('teams').document(team1_id).get()
    team2 = firestore_db.collection('teams').document(team2_id).get()

    if team1.exists and team2.exists:
        team1_data = team1.to_dict()
        team2_data = team2.to_dict()
        team_list = [{'id': team.id, 'name': team.to_dict().get('name')} for team in teams]  
        return templates.TemplateResponse('compare_teams.html', {
            'request': request,
            'team1': team1_data,
            'team2': team2_data,
            'teams': team_list
        })
    else:
        return templates.TemplateResponse('compare_teams.html', {
            'request': request,
            'error': 'One or both teams not found.'
        })
