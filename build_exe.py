# для компиляции необходимо прописать переменные среды
# NATASHA_DATA_PATH = C:\Users\User\AppData\Local\Programs\Python\Python311\Lib\site-packages\natasha\data
# PYMORPHY2_DICT_PATH = C:\Users\User\AppData\Local\Programs\Python\Python311\Lib\site-packages\pymorphy2_dicts_ru\data

import PyInstaller.__main__

PyInstaller.__main__.run(['main.py', '--onefile'])