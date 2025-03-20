import pytest
import os
from il_supermarket_scarper.utils.connection import wget_file


def test_wget_file_dont_exist():
    """Test wget file that does not exist"""
    with pytest.raises(FileNotFoundError):
        wget_file(
            "https://pricesprodpublic.blob.core.windows.net/price/Price7290027600007-036-202503181800.gz?sv=2014-02-14&sr=b&sig=Me8hez2oy5vClACdE5fVOyyu5Qef%2FlEJSQYfMvQAOKg%3D&se=2025-03-18T18%3A02%3A59Z&sp=r",
            "some_file.gz",
        )

    assert not os.path.exists("some_file.gz")
