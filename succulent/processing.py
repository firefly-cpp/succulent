import os
import pandas as pd

class Processing:
    def __init__(self, config):
        self.filetype = config['filetype']
        self.columns = [configuration['name'] for configuration in config['data']]
    
    def parameters(self):
        parameters = [f'{column}=' for column in self.columns]
        parameters = '&'.join(parameters)
        return parameters
        
    def process(self, req):
        # Define paths
        path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'data', f'data.{self.filetype}'
        )
        output_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'data', f'data.{self.filetype}'
        )

        # Load existing data
        if os.path.exists(path):
            if self.filetype == 'csv':
                df = pd.read_csv(path, sep=',')
            elif self.filetype == 'json':
                df = pd.read_json(path, orient='records')
            else:
                raise ValueError(f'Invalid file type: {self.filetype}')

        # Initialise new data
        else:
            df = pd.DataFrame(columns=self.columns)

        # Parse data from request
        if req.is_json:
            data = [req.json[column] for column in self.columns]
        else:
            data = [req.args.get(column) for column in self.columns]
        new_data = pd.Series(data, index=self.columns)

        # Merge data
        df = pd.concat([df, new_data.to_frame().T], ignore_index=True)

        # Store data to device
        match self.filetype:
            case 'csv':
                df.to_csv(output_path, sep=',', index=False)
            case 'json':
                df.to_json(output_path, orient='records', indent=4)
            case _:
                raise ValueError(f'Invalid file type: {self.filetype}')