from flask import Flask, request, render_template
import sqlite3
import json 

app = Flask(__name__)
