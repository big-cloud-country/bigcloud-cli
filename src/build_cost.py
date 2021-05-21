import pandas as pd

def build_cost(cost_filename, asset_name):
    #get csv file
    #load into pd df
    df = pd.read_csv(cost_filename)

    #clean it, do some interesting transformations
    #remove acknowledgements and stuff
    length = len(df)
    df.drop(inplace=True, index = length-1)
    df.drop(inplace=True, index = length-2)

    #write to js -- cost_input.js
    json_data = df.to_json(orient='records')
    file_contents = 'var costData = ' + json_data + ';'
    cost_json_filename = asset_name + '.js'

    #write the data just for this cost estimate
    text_file = open(cost_json_filename, "w")
    n = text_file.write(file_contents)
    text_file.close()

    #write a "master" cost input
    text_file = open('cost_input.js', "w")
    n = text_file.write(file_contents)
    text_file.close()
    return cost_json_filename