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

db = TinyDB('db.json')

PLAN_OPTIONS = [
    'data_pipeline_one_source',
    'data_platform_setup',
    'twilio_migration',
]
ASSET_BUCKET = 'big-cloud-country'
PROJECT_PLANS_FOLDER = 'project-plans'
TIMELINES_FOLDER = 'timelines'
COSTS_FOLDER = 'costs'

cost_assets = db.search(Query().asset=='costs')
cost_asset_names = []
for obj in cost_assets:
    cost_asset_names.append(obj['name'])
ASSET_NAMES = {
    'costs': cost_asset_names
}

s3 = boto3.resource('s3')

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



def download_file(asset_type, asset_name, source_filename=None):
    if asset_type=='plans':
        source_file = PROJECT_PLANS_FOLDER + '/' + source_filename + '.csv'
        destination_file = asset_name + '.csv'
    if asset_type=='timelines':
        source_file = TIMELINES_FOLDER + '/' + asset_type + '.html'
        destination_file = asset_name + '.html'
    if asset_type=='costs':
        source_file = COSTS_FOLDER + '/' + asset_type + '.html'
        destination_file = asset_name + '.html'
    #put it in a folder
    s3.Object(ASSET_BUCKET, source_file).download_file(destination_file)
    return destination_file


@plans.command()
@click.pass_context
@click.option('--type',
    default='data_platform_setup',
    prompt='What type of project plan?',
    show_default=True,
    type=click.Choice(PLAN_OPTIONS),)
@click.option('--name', '-d', prompt='Choose a unique name for this plan:') #add validation for this. can't have multiple unique namaes.
def new(ctx, type, name):
    #get the type
    #download the csv from s3
    download_file(
        ctx.obj['asset'],
        name,
        type
    )
    source_file = PROJECT_PLANS_FOLDER + '/' + type + '.csv'
    destination_file = name + '.csv'
    #put it in a folder
    s3.Object(ASSET_BUCKET, source_file).download_file(destination_file)
    #save it to a database
    db.insert({
        'asset': 'plans',
        'type': type,
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
@click.option('--name', '-n', prompt='Choose a unique name for this timeline')
@click.option('--plan_name', '-p', prompt='Name of the plan you want to use to generate the timeline')
def new(ctx, name, plan_name):
    #download the html file and rename it
    timelines_html = download_file(ctx.obj['asset'], name)

    #take the project plan
    #project_plan_csv = db.search(Query().name == plan_name)[0].path
    project_plan_csv = db.search(Query().name == plan_name)[0]['path']
    #build the input data
    #put the input.js file somewhere
    #output the html file.
    build_timeline(project_plan_csv, name)

    #suggest a command `open html.html`
    webbrowser.open('file://' + os.path.realpath(timelines_html))
    #insert into the db.
    pass


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
