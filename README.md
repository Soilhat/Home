# Home

## Prerequisites

### Python 

Install dependencies (suggest to use virtual environment) `pip install -r requirements.txt`

## How to use 

Add `instance/config.py` file following `instance/config_template.py` variable definition.

Run app :
`python -m flask --app flaskr`

## Woob Customization

insiide `woob\modules\3.6\woob_modules\bp\browser.py` file, `do_login` function L507 comment whole try except part
