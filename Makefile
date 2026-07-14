.PHONY: setup test run dashboard clean

setup:
	python -m pip install -r requirements.txt

test:
	python -m pytest -q

run:
	python main.py

dashboard:
	python -m pip install -r requirements-dashboard.txt
	streamlit run dashboard.py

clean:
	python scripts/clean_outputs.py
