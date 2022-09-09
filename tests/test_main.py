
import os,shutil,time
from il_supermarket_scarper.main import ScarpingTask
from il_supermarket_scarper.utils.status import get_all_listed_scarpers_class_names,get_output_folder

def test_main_with_limit():
    expected = get_all_listed_scarpers_class_names()
    output_folder = "test_dump"
    scrapper_done = ScarpingTask().start(limit=1,dump_folder_name=output_folder)

    folders_from_scraper = list(map(lambda x:x.split("/")[1],scrapper_done))

    time.sleep(5)
    folders_in_dump_folder = os.listdir(output_folder)
    folders_in_dump_folder = [name for name in folders_in_dump_folder if not name.startswith(".") ]
    assert len(folders_in_dump_folder) == len(expected)
    assert sorted(folders_from_scraper) == sorted(folders_in_dump_folder)
    

    for folder in folders_in_dump_folder:
        assert len(os.listdir(os.path.join(output_folder,folder))) >= 2
    
    shutil.rmtree(output_folder)


def test_main_with_one_scarper():
    scrapper_done = Main().start(limit=1,enabled_scrapers=["DorAlon"])
    assert "dor" in scrapper_done[0].lower() and "alon" in scrapper_done[0].lower()
    assert len(scrapper_done) == 1

def test_main_with_size_estimation_mode():
    scrapper_done = Main().start(limit=1,size_estimation_mode=True,enabled_scrapers=["DorAlon"])
    assert len(scrapper_done) == 0