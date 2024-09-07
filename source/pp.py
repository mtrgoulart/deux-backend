import configparser

class ConfigLoader:
    def __init__(self, config_file='config.ini'):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.config.read(config_file)
    
    def get(self, section, key):
        return self.config.get(section, key)

class Market:
    def __init__(self,symbol=None,order_type=None,side=None,size=None, price=None,operation=None,indicator=None):
        self.symbol=symbol
        self.order_type=order_type
        self.side=side
        self.size=size
        self.price=price
        self.operation=operation
        self.indicator=indicator

    def to_dict(self):
        return {
            "symbol": self.symbol,
            "order_type": self.order_type,
            "size": self.size,
            "side": self.side,
            "price": self.price,
            "operation":self.operation
        }
    

class Condition:
    def __init__(self,tp,sl,open_operations_condition,size,signals_condition):
        self.tp=tp
        self.sl=sl
        self.open_operations_condition=open_operations_condition
        self.size=size
        self.signals_condition=signals_condition
    

class WebhookData:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        # Initialize an empty list to store multiple data dictionaries
        if not hasattr(self, 'data_list'):
            self.data_list = []
        # Initialize an empty list to store Market objects
        if not hasattr(self, 'market_objects'):
            self.market_objects = []

    def add_data(self, data_str):
        # Parse the input string and append the parsed data to the list
        data_dict = self._parse_data(data_str)
        self.data_list.append(data_dict)

    def add_object(self, market_object):
        # Add a Market object to the market_objects list
        if isinstance(market_object, Market):
            self.market_objects.append(market_object)
        else:
            raise TypeError("Expected an instance of Market class.")
        
    def update_data_at_index(self, index, new_data):
        # Update the data at the given index
        if index < 0 or index >= len(self.data_list):
            raise IndexError("Index out of range.")
        self.data_list[index] = new_data

    def update_market_object_at_index(self, index, new_market_object):
        # Update the Market object at the given index
        if index < 0 or index >= len(self.market_objects):
            raise IndexError("Index out of range.")
        if not isinstance(new_market_object, Market):
            raise TypeError("Expected an instance of Market class.")
        self.market_objects[index] = new_market_object

    def _parse_data(self, data_str):
        # Split the string by commas, and then by equals sign to create a dictionary
        data_items = data_str.split(',')
        data_dict = {}
        for item in data_items:
            key, value = item.split('=')
            data_dict[key.strip()] = value.strip()
        return data_dict

    def get_data(self):
        # Return the list of all data dictionaries
        return self.data_list

    def get_data_at_index(self, index):
        # Return the data dictionary at a specific index
        if index < 0 or index >= len(self.data_list):
            raise IndexError("Index out of range.")
        return self.data_list[index]

    def get_market_objects(self):
        # Return the list of all Market objects
        return self.market_objects

    def get_market_object_at_index(self, index):
        # Return the Market object at a specific index
        if index < 0 or index >= len(self.market_objects):
            raise IndexError("Index out of range.")
        return self.market_objects[index]

    def __str__(self):
        # For printing the object data in a readable format
        return f"WebhookData(data_list={self.data_list}, market_objects={self.market_objects})"

    def get_value(self, key, index=0):
        # Get a specific value by key from a specific data dictionary
        if index < 0 or index >= len(self.data_list):
            raise IndexError("Index out of range.")
        return self.data_list[index].get(key, None)

    def get_last_n_data(self, n=2):
        # Get the last n data dictionaries from the list
        if n < 1:
            raise ValueError("The number of items to retrieve must be at least 1.")
        return self.data_list[-n:]
    
    def get_last_n_market(self, n=2):
        # Get the last n data dictionaries from the list
        if n < 1:
            raise ValueError("The number of items to retrieve must be at least 1.")
        return self.market_objects[-n:]
