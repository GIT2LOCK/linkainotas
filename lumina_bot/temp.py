from pywinauto import Application

for pid in (10784, 13820):
    print("=" * 100)
    print("PID:", pid)

    try:
        app = Application(backend="uia").connect(process=pid)

        window = app.top_window()

        window.print_control_identifiers()

    except Exception as e:
        print(e)