# Home

## Prerequisites

### Python 

Install dependencies (suggest to use virtual environment) `pip install -r requirements.txt`

## How to use 

Add `instance/config.py` file following `instance/config_template.py` variable definition.

Run app :
`python -m flask --app flaskr`

## Woob Customization

insiide `woob\modules\3.7\woob_modules\cragr\browser.py` file, `get_account_iban` function L645 add `HTTPNotFound` to except
insiide `woob\modules\3.7\woob_modules\lcl\browser.py` file, `connexion_bourse` function L577 add `or self.page is None` to if section to return False
