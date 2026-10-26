// [wasm-port] Stub for the GLFW backend of ImGui. IMGUIGLViewImpl.cpp calls only Init/MouseButtonCallback/
// ScrollCallback/CharCallback; the rest are here for completeness. The debug ImGui panel is not enabled on
// Emscripten, so the backend does not need to do anything.
#include "imgui.h"
#include "imgui_impl_glfw.h"

bool ImGui_ImplGlfw_Init(GLFWwindow*, bool) { return true; }
void ImGui_ImplGlfw_Shutdown() {}
void ImGui_ImplGlfw_NewFrame() {}
void ImGui_ImplGlfw_InvalidateDeviceObjects() {}
bool ImGui_ImplGlfw_CreateDeviceObjects() { return true; }
bool ImGui_ImplIOS_CreateFontsTexture() { return true; }
void ImGui_ImplGlfw_MouseButtonCallback(GLFWwindow*, int, int, int) {}
void ImGui_ImplGlfw_ScrollCallback(GLFWwindow*, double, double) {}
void ImGui_ImplGlFw_KeyCallback(GLFWwindow*, int, int, int, int) {}
void ImGui_ImplGlfw_CharCallback(GLFWwindow*, unsigned int) {}
