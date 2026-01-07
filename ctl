#!/bin/bash

# Quick wrapper script for common operations

case "$1" in
    start|up)
        ./start.sh
        ;;
    rebuild)
        ./start.sh --rebuild
        ;;
    stop|down)
        docker-compose down
        ;;
    restart)
        docker-compose restart
        ;;
    logs)
        shift
        docker-compose logs -f "$@"
        ;;
    status|ps)
        docker-compose ps
        ;;
    shell|sh)
        shift
        docker-compose exec "$@"
        ;;
    db)
        docker-compose exec postgres psql -U seoman -d seoman
        ;;
    redis)
        docker-compose exec redis redis-cli -a seoman_dev_password
        ;;
    clean)
        echo "This will remove all containers, volumes, and images. Continue? (y/N)"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            docker-compose down -v --remove-orphans
            docker system prune -af
        fi
        ;;
    *)
        echo "Usage: $0 {start|rebuild|stop|restart|logs|status|shell|db|redis|clean} [args]"
        echo ""
        echo "Commands:"
        echo "  start       Start services and create admin user"
        echo "  rebuild     Rebuild containers without cache and start"
        echo "  stop        Stop all services"
        echo "  restart    Restart all services"
        echo "  logs        View logs (optional: specify service name)"
        echo "  status      Show service status"
        echo "  shell       Execute command in container (e.g., $0 shell backend bash)"
        echo "  db          Access database shell"
        echo "  redis       Access Redis CLI"
        echo "  clean       Remove all containers, volumes, and images"
        echo ""
        exit 1
        ;;
esac
