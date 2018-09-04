from aiohttp import web
import asyncio
import os
from configparser import ConfigParser



users = {}
persistMessages = {}



def loadConfig(runConfig):
  # загружает дефолтную конфигурацию
  config = ConfigParser()
  with open(os.path.join(os.path.dirname(__file__), 'default.config')) as defaultJsonConfig:
    config.read_file(defaultJsonConfig)

  # загружает файл с продакшена
  if runConfig:
    config.read_file(runConfig)
  return config



async def sendMessageToWebsocket(websocket, type, data):
  # Отсылка сообщения в открытый websocket.
  if not websocket.closed:
    await websocket.send_json({
      "type": type,
      "data": data
    })



async def sendNotificationHandler(request):
  # Принимает, валидирует сообщение и пытается отослать его через websocket.
  # Если сообщение с ключем persist то сохраняет его для отсылки при первом подключении.
  message = await request.json()

  if "type" not in message:
    raise web.HTTPBadRequest(text = "Не хватает типа сообщения")

  if "data" not in message:
    raise web.HTTPBadRequest(text = "Не хватает данных сообщения")

  for userId, value in message["data"].items():
    targetUser = int(userId)
    if targetUser in users:
      for websocket in users[targetUser]:
        await sendMessageToWebsocket(websocket, message["type"], value)

      # если есть ключ persist то сохраняет сообщение для того чтобы отослать из при подключении вэбсокета
      if "persist" in message:
        if targetUser not in persistMessages:
          persistMessages[targetUser] = {}
        persistMessages[targetUser][message["type"]] = value

  return web.Response(text = "ok")




async def getOnlineUserIdList(request):
  onlineUserList = []
  for userId, websockets in users.items():
    if websockets:
      onlineUserList.append(userId)
  return web.json_response(onlineUserList)




async def websocketHandler(request):
  userId = int(request.match_info['userId'])

  ws = web.WebSocketResponse()
  await ws.prepare(request)

  try:
    # Добавление открытого сокета в пользователя.
    if userId not in users:
      users[userId] = [ws]
    else:
      users[userId].append(ws)

    # Отсылка пользователю всех запомненых сообщений.
    if userId in persistMessages:
      for type, value in persistMessages[userId].items():
        await sendMessageToWebsocket(ws, type, value)

    # Получение входящих сообщений,
    # но так как они нам не нужны то я просто печатаю их.
    async for msg in ws:
      print(msg)

  finally:
    await ws.close()
  return ws



# Удаляет закрытые вэбсокеты из пула.
async def removeClosedWebsocket(app):
  try:
    for user, websockets in users.items():
      for webcosket in websockets:
        if webcosket.closed:
          websockets.remove(webcosket)
  finally:
    await asyncio.sleep(60)
    app.loop.create_task(removeClosedWebsocket(app))



def createMainApp(config = None):
  loop = asyncio.get_event_loop()
  app = web.Application(loop = loop)
  app["config"] = loadConfig(config)
  app.loop.create_task(removeClosedWebsocket(app))
  app.router.add_post("/api/sendNotification", sendNotificationHandler)
  app.router.add_get("/api/onlineUserList/", getOnlineUserIdList)
  app.router.add_get('/ws/{userId}', websocketHandler)
  return app