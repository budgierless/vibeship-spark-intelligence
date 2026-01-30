@echo off
cd /d %~dp0..
python -m spark.cli services
