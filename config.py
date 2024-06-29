import yaml
import logging

# Configuração do logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler = logging.FileHandler('market_sniper.log', mode='w')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

def load_config():
    print("Loading config file...")
    logger.debug("Loading config file...")
    with open('settings/config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    url_info = [[None]*5 for _ in range(len(config['skins']))]

    # Access the products list and loop over each product
    for idx, skin in enumerate(config['skins']):
        # Access the URL and its parameters for each product
        url_info[idx][0] = skin['float']
        url_info[idx][1] = skin['number_of_stickers']
        url_info[idx][2] = skin['price']
        url_info[idx][3] = skin['pages']
        url_info[idx][4] = skin['url']

        if url_info[idx][4] is None:
            print("There is skin that have URL empty in config.yaml.\nExiting...")
            return None

    print(f"Loaded {len(url_info)} skins!")
    logger.debug(f"Config loaded: {url_info}")
    return url_info