# IWantToBuyACarWithGoodPrice - The Machine Learning project for me to not overspend to buy a car

A Machine Learning project to predict a good price to pay for used car you want to buy with inputs (brand, mileage, transmission).

---
## Pipeline Architecture
It will follow step by step:
1. **Scraping data**: The spiders will scrape data from websites such as Autotrader, Kijiji
2. **Normalize data**: After having crawled data (raw data), we will normalize it for better performance
3. **Merge data**: Then we merge data from each json result from every spider to a final result.json
4. **Train and predict**: And we use the result.json file to train model (RandomForestRegressor) and then you can input car details you want to buy and it will predict the good price for you

---
## Requirements
- Python 3.10+
You need to have **Microsoft Edge WebDriver (`msedgedriver.exe`)** put inside the repo folder or set the path in file by your own.

---
## Setup locally
### Clone repo:
```bash
git clone https://github.com/GiaHuyTang/IWantToBuyACarWithGoodPrice.git
cd IWantToBuyACarWithGoodPrice
```

### Create and activate envinronment
```bash
python -m venv .venv
.venv\Scripts\activate
```

### Install dependencies
```bash
pip install -r requirements.txt
```

---
## How to run
I will pretend I want to buy a used Mini car and show you how to run it properly.

### 1. Scraping Data and Normalize
We will run spiders to scrape raw data from websites, I use 2 spiders currently (Autotrader_spider.json is broken - I'm fixing it).
```bash
python spiders/kijiji_spider.py --brand mini 
```

you will need to run every spider manually, and data normalization is in every spider already.
It is annoying but I'm newbie so please understand for me T_T.

### 2. Merge data
```bash
python merge_results.py 
```

### 3. Train and Predict
And this step, you just need to set arguments for it, I will give you example: the car I want to buy is Mini Countryman 2014 with 120,000KM mileage and Auto transmission.
```bash
python predicts_car_price.py
```
Arguments:
--brand : Brand name (Ex: mini, toyota, honda).
--location : location (not used, default canada).

And it will give you a predicted price.

## Folder structure
```
IWantToBuyACarWithGoodPrice/
│
├── spiders/                #Scrawling Scripts
│   └── autotrader_spider.py 
│   └── kijiji_spider.py  
├── results/                #Results storage    
├── merge_results.py        #Merging all scrawled results 
├── predicts_car_price.py   #Predict model    
├── .gitignore
└── README.md
```
---
## Author
Gia Huy Tang - Business Information Systems student at Saskatchewan Polytechnic
