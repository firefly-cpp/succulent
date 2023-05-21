import os
import pandas as pd

class Processing:
    def __init__(self, config, format):
        self.format = format
        self.columns = [configuration['name'] for configuration in config['data']]
    
    def parameters(self):
        parameters = [f'{column}=' for column in self.columns]
        parameters = '&'.join(parameters)
        return parameters
        
    def process(self, req):
        # Define paths
        path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'data', f'data.{self.format}'
        )
        output_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'data', f'data.{self.format}'
        )

        # Load existing data
        if os.path.exists(path):
            if self.format == 'csv':
                df = pd.read_csv(path, sep=',')
            elif self.format == 'json':
                df = pd.read_json(path, orient='records')
            else:
                raise ValueError(f'Invalid file type: {self.format}')
        # Initialise new data
        else:
            df = pd.DataFrame(columns=self.columns)

        # Parse data from request
        data = {}
        if req.is_json:
            for column in self.columns:
                try:
                    data[column] = req.json[column]
                except:
                    data[column] = None
        else:
            for column in self.columns:
                try: 
                    data[column] = req.args.get(column)
                except:
                    data[column] = None
        data = pd.Series(data, index=self.columns)

        # Merge data
        df = pd.concat([df, data.to_frame().T], ignore_index=True)

        # Store data to device
        if self.format == 'csv':
            df.to_csv(output_path, sep=',', index=False)
        elif self.format == 'json':
            df.to_json(output_path, orient='records', indent=4)
        else:
            raise ValueError(f'Invalid format: {self.format}')