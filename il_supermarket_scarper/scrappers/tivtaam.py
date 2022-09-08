from il_supermarket_scarper.engines import Cerberus


class TivTaam(Cerberus):

    def __init__(self,folder_name=None):
        super().__init__("Tiv Taam", chain_id="7290873255550", folder_name=folder_name, ftp_username="TivTaam")
    
