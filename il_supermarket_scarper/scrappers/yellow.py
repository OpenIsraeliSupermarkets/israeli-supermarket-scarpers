from il_supermarket_scarper.engines import Cerberus


class Yellow(Cerberus):

    def __init__(self,folder_name=None):
        super().__init__("Yellow", chain_id="7290644700005", folder_name=folder_name, ftp_username="Paz_bo",ftp_password="paz468")
    
