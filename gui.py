import PySimpleGUI as sg

# Initial input fields
input_fields = ['']

def create_layout(inputs):
    layout = [
        [sg.Text("Main Textbox")],
        [sg.Multiline(size=(40, 5), key='-TEXTBOX-')],
        [sg.Text("Dynamic Inputs")]
    ]
    for i, val in enumerate(inputs):
        layout.append([sg.Input(default_text=val, key=f'-IN-{i}-')])
    layout.append([sg.Button("Start")])
    return layout

window = sg.Window("Dynamic Input App", create_layout(input_fields))

while True:
    event, values = window.read()

    if event == sg.WIN_CLOSED:
        break

    # Check if we need to add a new input
    last_key = f'-IN-{len(input_fields)-1}-'
    if values.get(last_key):
        input_fields.append('')
        window.close()
        window = sg.Window("Dynamic Input App", create_layout(input_fields))
        continue

    if event == "Start":
        main_text = values['-TEXTBOX-']
        inputs = [values[f'-IN-{i}-'] for i in range(len(input_fields)) if values[f'-IN-{i}-'].strip() != '']
        print("Main Text:", main_text)
        print("Inputs:", inputs)

window.close()