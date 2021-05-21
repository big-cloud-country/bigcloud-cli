# import click
#
#
# #groups get executed before any subcommand
# #add in home directory for where to store various files
# #https://youtu.be/kNke39OZ2k0?t=1032

import click
import boto3
from tinydb import TinyDB, Query
import webbrowser
import os
from src.build_timeline import build_timeline
from src.build_cost import build_cost
import shutil
import inquirer
import yaml

db = TinyDB('db.json')

#move this to a list of s3 object
PLAN_OPTIONS = [
    'data_pipeline_one_source',
    'data_platform_setup',
    'twilio_migration',
]
ASSET_BUCKET = 'big-cloud-country'
PROJECT_PLANS_FOLDER = 'templates/project_plans'
TIMELINES_FOLDER = 'templates/timelines'
COSTS_FOLDER = 'templates/costs'
PRICING_OPTIONS_FOLDER = 'templates/pricing_options'
PRICING_OPTIONS_TEMPLATE_FILE = 'pricing_options_template.yaml'
PRICING_OPTIONS_HTML_FILE = 'pricing-options.html'

#build option lists
cost_assets = db.search(Query().asset=='costs')
cost_asset_names = []
for obj in cost_assets:
    cost_asset_names.append(obj['name'])

plan_assets = db.search(Query().asset=='plans')
plan_asset_names = []
for obj in plan_assets:
    plan_asset_names.append(obj['name'])


timeline_assets = db.search(Query().asset=='timelines')
timeline_asset_names = []
for obj in timeline_assets:
    timeline_asset_names.append(obj['name'])


ASSET_NAMES = {
    'costs': cost_asset_names,
    'plans': plan_asset_names,
    'timelines': timeline_asset_names,
}

s3 = boto3.resource('s3')


def download_file(asset_type, asset_name, source_filename=None):
    files_to_download = []
    if asset_type=='plans':
        files_to_download.append({
            'source': PROJECT_PLANS_FOLDER + '/' + source_filename + '.csv',
            'destination': asset_name + '.csv',
        })
    if asset_type=='timelines':
        files_to_download.append({
            'source': TIMELINES_FOLDER + '/' + asset_type + '.html',
            'destination': asset_name + '.html',
        })
    if asset_type=='costs':
        files_to_download.append({
            'source': COSTS_FOLDER + '/' + asset_type + '.html',
            'destination': asset_name + '.html',
        })
    if asset_type=='options':
        files_to_download.append({
            'source': PRICING_OPTIONS_FOLDER + '/' + PRICING_OPTIONS_TEMPLATE_FILE,
            'destination': asset_name + '.yaml',
        })
        files_to_download.append({
            'source': PRICING_OPTIONS_FOLDER + '/' + PRICING_OPTIONS_HTML_FILE,
            'destination': asset_name + '.html',
        })
    #put it in a folder
    for f in files_to_download:
        s3.Object(ASSET_BUCKET, f['source']).download_file(f['destination'])
    return files_to_download



@click.group()
@click.option('--debug/--no-debug', default=False)
@click.pass_context
def cli(ctx, debug):
    # ensure that ctx.obj exists and is a dict (in case `cli()` is called
    # by means other than the `if` block below)
    ctx.ensure_object(dict)
    #ctx.obj['DEBUG'] = debug
    #ctx.obj['primary'] = 'proposal'

@cli.group()
def assets():
    pass

@assets.command()
@click.option('--name', '-n')
def delete(name):
    db.remove(Query().name == name)
    click.echo('deleted ' + name)
    click.echo('Updated project assets:\n')
    for item in iter(db):
        click.echo(item)

@assets.command()
def list():
    for item in iter(db):
        click.echo(item)

"""
PLANS
"""
@cli.group()
@click.pass_context
def plans(ctx):
    ctx.obj['asset'] = 'plans'


@plans.command()
@click.pass_context
@click.option('--name', '-d', prompt='Choose a unique name for this plan:') #add validation for this. can't have multiple unique namaes.
def new(ctx, name):
    #get the type
    questions = [inquirer.List('plan_type',
                              message='Which baseline plan?',
                              choices=PLAN_OPTIONS)]
    answer = inquirer.prompt(questions)
    download_file(
        ctx.obj['asset'],
        name,
        answer['plan_type']
    )
    #save it to a database
    db.insert({
        'asset': 'plans',
        'type': answer['plan_type'],
        'name': name,
        'path': os.path.realpath(name + '.csv'),
    })

@plans.command()
@click.pass_context
@click.option('--name', '-n', prompt='Which plan name?')
def show(ctx, name):
    #subprocess.run('idea ' + name + '.csv')

    webbrowser.open('file://' + os.path.realpath(name + '.csv'))

"""
TIMELINES
"""
@cli.group()
@click.pass_context
def timelines(ctx):
    ctx.obj['asset'] = 'timelines'

@timelines.command()
@click.pass_context
#@click.option('--name', '-n', prompt='Choose a unique name for this timeline')
#@click.option('--plan_name', '-p', prompt='Name of the plan you want to use to generate the timeline')
def new(ctx):
    #download the html file and rename it
    questions = [inquirer.List('plan_name',
                               message='Which plan do you want to build a timeline for?',
                               choices=ASSET_NAMES['plans'])]
    answers = inquirer.prompt(questions)

    plan_name = answers['plan_name']

    name='timeline_for_' + plan_name
    timelines_html = download_file(ctx.obj['asset'], name)[0]['destination']

    #take the project plan
    #project_plan_csv = db.search(Query().name == plan_name)[0].path
    project_plan_csv = db.search(Query().name == plan_name)[0]['path']
    #build the input data
    #put the input.js file somewhere
    #output the html file.
    print(project_plan_csv)
    plan_numbers = build_timeline(project_plan_csv, name)


    #suggest a command `open html.html`
    webbrowser.open('file://' + os.path.realpath(timelines_html))
    #insert into the db.
    db.insert({
        'asset': ctx.obj['asset'],
        'name': name,
        'path': timelines_html,
    })
    #save the metadata for later
    db.insert({
        'asset': 'options',
        'name': 'options_for_' + name,
        'plan_name': plan_name,
        'plan_numbers': plan_numbers,
    })


def show():
    pass
"""
PROPOSALS
"""
@cli.group()
@click.pass_context
def proposals(ctx):
    click.echo('proposals')
    ctx.obj['asset'] = 'proposals'

@proposals.command()
@click.pass_context
def new(ctx):
    click.echo(ctx.obj['asset'])
    ctx.obj['action'] = 'new'
    click.echo(ctx.obj['action'])

@proposals.command()
@click.pass_context
def show(ctx):
    click.echo(ctx.obj['asset'])
    ctx.obj['action'] = 'show'
    click.echo(ctx.obj['action'])

"""
CLOUD COST ESTIMATE s
"""
@cli.group()
@click.pass_context
def costs(ctx):
    ctx.obj['asset'] = 'costs'

@costs.command()
@click.pass_context
@click.option('--name', '-n', prompt='Choose a unique name for this cost estimate')
@click.option('--cost_filename', '-c', prompt='Unedited CSV file that contains the AWS cost estimate')
def new(ctx, name, cost_filename):
    cost_html = download_file(
        ctx.obj['asset'],
        name,
    )
    f = os.path.realpath(cost_filename)
    cost_json_filename = build_cost(f, name)
    webbrowser.open('file://' + os.path.realpath(cost_html))

    #then open the html file with the inputs
    #save the cost to the db
    db.insert({
        'asset': ctx.obj['asset'],
        'name': name,
        'path': os.path.realpath(cost_html),
        'input_data': os.path.realpath(cost_json_filename)
    })

@costs.command()
@click.pass_context
@click.option('--name', '-n', prompt='The name for the cost estimate you want to view', type=click.Choice(ASSET_NAMES['costs']))
def show(ctx, name):
    #get the html filename
    cost_record = db.search(Query().name == name)[0]
    cost_json = cost_record['input_data']
    cost_html = cost_record['path']
    #copy the json input file, and rename it cost_input.js
    master_json = 'cost_input.js'
    shutil.copy(cost_json, master_json)
    #open the file
    webbrowser.open('file://' + os.path.realpath(cost_html))


"""
PRICING OPTIONSs
"""
@cli.group()
@click.pass_context
def options(ctx):
    ctx.obj['asset'] = 'options'

@options.command()
@click.pass_context
@click.option('--name', '-n', prompt='Enter a name for your set of pricing options')
def new(ctx, name):
    questions = [
        inquirer.Checkbox('chosen_plans',
                          message='Which plans do you want to include?',
                          choices=ASSET_NAMES['plans'])
    ]
    answers=inquirer.prompt(questions)
    options = {
        'plan_options': []
    }
    yaml_template = name + '_pricing_options.yaml'

    for idx, chosen_plan in enumerate(answers['chosen_plans']):
        #get the metadata
        q = (Query().asset =='options') & (Query().plan_name==chosen_plan)
        option_return = db.search(q)

        #[0]['plan_numbers']
        #build a dict
        if len(option_return)>0:
            option_data = option_return[0]
            option_data['name'] = 'Option ' + str(idx + 1)
            option_data['extras'] = 'Extra features here'
            option_data['discount'] = '0'
            option_data['path'] = yaml_template
            options['plan_options'].append({
                'discount': option_data['discount'],
                'extras': option_data['extras'],
                'name': option_data['name'],
                'project_cost': option_data['plan_numbers']['project_cost'],
                'project_weeks': option_data['plan_numbers']['project_weeks'],
                'project_days': option_data['plan_numbers']['project_days'],
                'project_cost_after_discount': '',
                'monthly_cost': option_data['plan_numbers']['monthly_cost']

            })
            db.update(option_data, q)

    #build the yaml and write it
    with open(yaml_template, 'w') as file:
        yaml.dump(options, file)

def show(ctx, name):
    options_html = download_file(ctx.obj['asset'], name)

@options.command()
def test():
    questions = [
        inquirer.Checkbox('interests',
                          message="What are you interested in?",
                          choices=['Computers', 'Books', 'Science', 'Nature', 'Fantasy', 'History'],
                          ),
    ]
    answers = inquirer.prompt(questions)
    #show
    #build a csv from yaml
    #tell them where the csv is, and they can make a table from it.
    #also build a .js file
    #html table with bootstrap
       # 'input_data': os.path.realpath(cost_json_filename)
