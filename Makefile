.PHONY: setup test run dashboard copilot memo eval-rag clean

setup:
	python -m pip install -r requirements.txt

test:
	python -m pytest -q

run:
	python main.py

dashboard:
	python -m pip install -r requirements-dashboard.txt
	streamlit run dashboard.py

copilot:
	python rag_copilot.py "Why did the optimizer select the current warehouse network?"

memo:
	python rag_copilot.py --memo "Recommend the supply-chain network decision to executives"

eval-rag:
	python rag_copilot.py --evaluate

clean:
	python scripts/clean_outputs.py
