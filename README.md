# Indestructables
Indestructables is a privacy-respecting frontend to Instructables

# Instances
None, yet!

# Run your own instance
## Dependencies
`pip3 install -r requirements.txt`.

For the production environment, you also need the uWSGI Python3 plugin. On Debian, it can be installed via `apt install uwsgi-plugin-python3`
## Production
1. Clone the repository
2. Run `uwsgi --plugin python3 --http-socket 0.0.0.0:8002 --wsgi-file main.py --callable app --processes 4 --threads 2`
3. Point your reverse proxy to http://localhost:8002
## Development
1. Clone the repository
2. Run `python3 main.py`
3. Connect to http://localhost:8002