# Maintenance Task Setup

## Option 1: Docker Cron Job
Create a new Dockerfile that includes cron:

```dockerfile
FROM python:3.10-slim

# Install cron
RUN apt-get update && apt-get -y install cron

# Create cron job file
RUN echo "0 0 * * * cd /app && python src/maintenance.py >> /var/log/cron.log 2>&1" > /etc/cron.d/maintenance-cron
RUN chmod 0644 /etc/cron.d/maintenance-cron

# Apply cron job
RUN crontab /etc/cron.d/maintenance-cron

# Create log file
RUN touch /var/log/cron.log

# Start cron in foreground
CMD ["cron", "-f"]
```

## Option 2: System Cron Job
On your host system, add to crontab:
```bash
# Edit crontab
crontab -e

# Add this line to run maintenance daily at midnight
0 0 * * * cd /path/to/project && docker-compose run --rm maintenance
```

## Option 3: Docker Compose with Restart Policy
Add to your docker-compose.yml:
```yaml
services:
  maintenance:
    build:
      context: .
      dockerfile: docker/maintenance.Dockerfile
    restart: always
    environment:
      - TZ=UTC
    command: >
      sh -c "while true; do
        python src/maintenance.py;
        sleep 86400;
      done"
```

## Recommended Setup
For this project, I recommend Option 2 (System Cron Job) because:
1. It's the simplest to implement
2. It uses the existing Docker setup
3. It's easy to monitor and debug
4. It doesn't require additional containers running

### Implementation Steps:
1. Create a shell script to run maintenance:
```bash
#!/bin/bash
# maintenance.sh
cd /path/to/project
docker-compose run --rm maintenance
```

2. Make it executable:
```bash
chmod +x maintenance.sh
```

3. Add to crontab:
```bash
0 0 * * * /path/to/project/maintenance.sh >> /path/to/project/logs/maintenance.log 2>&1
```

### Monitoring
- Check logs in `/path/to/project/logs/maintenance.log`
- Set up log rotation to prevent log files from growing too large
- Consider adding email notifications for maintenance failures

### Testing
Before setting up the cron job:
1. Run the maintenance script manually to ensure it works
2. Test the shell script
3. Monitor the first few automated runs 
