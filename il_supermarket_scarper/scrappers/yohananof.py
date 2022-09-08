from il_supermarket_scarper.engines import Cerberus


class Yohananof(Cerberus):


    def __init__(self,folder_name=None):
        super().__init__("Yohananof", chain_id="290803800003", folder_name=folder_name, ftp_username="yohananof")
    