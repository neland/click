#pragma once
#include <windows.h>
#include "common_types.h"

// Show modal dialog to edit task. Returns true if OK pressed, fills outTask.
// If inOutTask.id != 0, dialog is in edit mode and loads existing values.
bool ShowTaskDialog(HWND parent, HINSTANCE hInst, ClickTask& inOutTask);
