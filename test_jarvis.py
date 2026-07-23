import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Add current folder to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

import JARVIS

class TestJarvis(unittest.TestCase):

    def test_clean_response(self):
        """Test that clean_response removes non-ASCII characters and strips whitespace."""
        self.assertEqual(JARVIS.clean_response("  Hello World! \n"), "Hello World!")
        self.assertEqual(JARVIS.clean_response("Jarvis 😊"), "Jarvis")
        self.assertEqual(JARVIS.clean_response("Café"), "Caf")

    def test_parse_ai_action_structured(self):
        """Test parsing of structured action and values (case-insensitive)."""
        # Upper case
        action, value = JARVIS.parse_ai_action("ACTION: OPEN_WEBSITE\nVALUE: https://google.com")
        self.assertEqual(action, "OPEN_WEBSITE")
        self.assertEqual(value, "https://google.com")

        # Lower case
        action, value = JARVIS.parse_ai_action("action: search_google\nvalue: deepseek llama")
        self.assertEqual(action, "SEARCH_GOOGLE")
        self.assertEqual(value, "deepseek llama")

        # Mixed whitespace and carriage return
        action, value = JARVIS.parse_ai_action("ACTION:   volume_up   \r\n VALUE: none ")
        self.assertEqual(action, "VOLUME_UP")
        self.assertEqual(value, "none")

    def test_parse_ai_action_keyword_fallback(self):
        """Test parsing fallback to keywords when no structured action is present."""
        action, value = JARVIS.parse_ai_action("Could you please increase volume or make it louder?")
        self.assertEqual(action, "VOLUME_UP")
        self.assertIsNone(value)

        action, value = JARVIS.parse_ai_action("Let's lower the sound, please volume_down.")
        self.assertEqual(action, "VOLUME_DOWN")
        self.assertIsNone(value)

        action, value = JARVIS.parse_ai_action("Please mute the system.")
        self.assertEqual(action, "MUTE")
        self.assertIsNone(value)

        action, value = JARVIS.parse_ai_action("Can you unmute please?")
        self.assertEqual(action, "UNMUTE")
        self.assertIsNone(value)

        action, value = JARVIS.parse_ai_action("Shut down immediately.")
        self.assertEqual(action, "SHUTDOWN")
        self.assertIsNone(value)

        action, value = JARVIS.parse_ai_action("Please restart the OS.")
        self.assertEqual(action, "RESTART")
        self.assertIsNone(value)

    def test_parse_ai_action_no_action(self):
        """Test returning None, None when no action is found."""
        action, value = JARVIS.parse_ai_action("Hello, how are you doing today?")
        self.assertIsNone(action)
        self.assertIsNone(value)

        action, value = JARVIS.parse_ai_action("")
        self.assertIsNone(action)
        self.assertIsNone(value)

    @patch("JARVIS.webbrowser.open")
    @patch("JARVIS.speak")
    def test_execute_action_webbrowser(self, mock_speak, mock_web_open):
        """Test execute_action for OPEN_WEBSITE and SEARCH_GOOGLE."""
        JARVIS.execute_action("OPEN_WEBSITE", "https://youtube.com")
        mock_web_open.assert_called_once_with("https://youtube.com")
        mock_speak.assert_called_once_with("Opening")

        mock_web_open.reset_mock()
        mock_speak.reset_mock()

        JARVIS.execute_action("SEARCH_GOOGLE", "python testing")
        mock_web_open.assert_called_once_with("https://www.google.com/search?q=python testing")
        mock_speak.assert_called_once_with("Searching")

    @patch("JARVIS.os.system")
    @patch("JARVIS.speak")
    def test_execute_action_system(self, mock_speak, mock_os_system):
        """Test execute_action for APP, SHUTDOWN, RESTART."""
        JARVIS.execute_action("OPEN_APP", "notepad")
        mock_os_system.assert_called_once_with("start notepad")
        mock_speak.assert_called_once_with("Opening app")

        mock_os_system.reset_mock()
        mock_speak.reset_mock()

        JARVIS.execute_action("SHUTDOWN", None)
        mock_os_system.assert_called_once_with("shutdown /s /t 5")
        mock_speak.assert_called_once_with("Shutting down")

        mock_os_system.reset_mock()
        mock_speak.reset_mock()

        JARVIS.execute_action("RESTART", None)
        mock_os_system.assert_called_once_with("shutdown /r /t 5")
        mock_speak.assert_called_once_with("Restarting")

    @patch("JARVIS.set_volume")
    def test_execute_action_volume(self, mock_set_volume):
        """Test execute_action for volume controls."""
        JARVIS.execute_action("VOLUME_UP", None)
        mock_set_volume.assert_called_once_with("up")

        mock_set_volume.reset_mock()
        JARVIS.execute_action("VOLUME_DOWN", None)
        mock_set_volume.assert_called_once_with("down")

        mock_set_volume.reset_mock()
        JARVIS.execute_action("MUTE", None)
        mock_set_volume.assert_called_once_with("mute")

        mock_set_volume.reset_mock()
        JARVIS.execute_action("UNMUTE", None)
        mock_set_volume.assert_called_once_with("unmute")

    @patch("JARVIS.chat_with_ai")
    @patch("JARVIS.parse_ai_action")
    @patch("JARVIS.execute_action")
    @patch("JARVIS.speak")
    def test_handle_command_action(self, mock_speak, mock_exec, mock_parse, mock_chat):
        """Test handle_command when an action is parsed."""
        mock_chat.return_value = "ACTION: OPEN_WEBSITE\nVALUE: test.com"
        mock_parse.return_value = ("OPEN_WEBSITE", "test.com")

        JARVIS.handle_command("jarvis open youtube")

        mock_chat.assert_called_once_with("open youtube")
        mock_parse.assert_called_once_with("ACTION: OPEN_WEBSITE\nVALUE: test.com")
        mock_exec.assert_called_once_with("OPEN_WEBSITE", "test.com")
        mock_speak.assert_not_called()

    @patch("JARVIS.chat_with_ai")
    @patch("JARVIS.parse_ai_action")
    @patch("JARVIS.execute_action")
    @patch("JARVIS.speak")
    def test_handle_command_conversational(self, mock_speak, mock_exec, mock_parse, mock_chat):
        """Test handle_command for general conversational prompts with no action."""
        mock_chat.return_value = "Hello! I am Jarvis."
        mock_parse.return_value = (None, None)

        JARVIS.handle_command("hello")

        mock_chat.assert_called_once_with("hello")
        mock_parse.assert_called_once_with("Hello! I am Jarvis.")
        mock_exec.assert_not_called()
        mock_speak.assert_called_once_with("Hello! I am Jarvis.")

if __name__ == "__main__":
    unittest.main()
