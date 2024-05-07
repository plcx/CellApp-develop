缺什么补什么，
进入虚拟环境nuclie
用pyinstaller app.py命令打包
ImportError: cannot import name 'CacheDataset' from partially initialized module 'monai.data' (most likely due to a circular import) (E:\NucleiSegmentation\CellApp-develop\dist\app\monai\data\__init__.pyc)
ModuleNotFoundError: No module named 'ml_dtypes'
ModuleNotFoundError: No module named 'skimage.filters.edges'
打开anacoda搜索
ml_dtypes
monai
skimage
复制到app.exe的dist\app目录里
复制工程目录的static到app.exe的dist\app目录里