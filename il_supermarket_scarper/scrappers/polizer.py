from il_supermarket_scarper.engines import Cerberus


class Polizer(Cerberus):


    def __init__(self,folder_name=None):
        super().__init__("Polizer", chain_id="7291059100008", folder_name=folder_name, ftp_username="politzer")
    