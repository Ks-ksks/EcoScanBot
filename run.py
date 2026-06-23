#!/usr/bin/env python
import os
import threading
import time
import httpx

def run_api():
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port)

def run_bot():
    from bot import EcoBot
    bot = EcoBot()
    bot.run()

if __name__ == "__main__":
    print("EcoBot")
    
    # API в фоне
    api_thread = threading.Thread(target=run_api, daemon=False)
    api_thread.start()
    print("API запущен")

    for i in range(5):
        try:
            response = httpx.get("http://localhost:8080/api/health", timeout=2)
            if response.status_code == 200:
                print("API готов")
                break
        except:
            print(f"Ожидание API... {i+1}/5")
            time.sleep(2)
    else:
        print("API не ответил, продолжаем...")
    
    # Бот в главном потоке
    run_bot()