import unittest
from unittest.mock import patch
from rich_pyfiglet import RichFiglet
from menu import (
    print_banner,
    show_menu,
    get_user_choice,
    prompt_repo_input,
    prompt_report_format,
    confirm_exit,
)


class TestPrintBanner(unittest.TestCase):
    @patch("menu.Console")
    def test_print_banner_outputs_lines(self, mock_console_cls):
        print_banner()

        mock_console_cls.return_value.print.assert_called_once()

    @patch("menu.Console")
    def test_print_banner_renders_figlet_banner(self, mock_console_cls):
        print_banner()

        banner = mock_console_cls.return_value.print.call_args[0][0]
        self.assertIsInstance(banner, RichFiglet)


class TestShowMenu(unittest.TestCase):
    @patch("builtins.print")
    def test_show_menu_prints_numbered_choices(self, mock_print):
        choices = ["Option A", "Option B", "Option C"]

        show_menu(choices)

        calls = [call[0][0] for call in mock_print.call_args_list]
        self.assertIn("1. Option A", calls)
        self.assertIn("2. Option B", calls)
        self.assertIn("3. Option C", calls)

    @patch("builtins.print")
    def test_show_menu_with_empty_choices(self, mock_print):
        choices = []

        show_menu(choices)

        mock_print.assert_not_called()

    @patch("builtins.print")
    def test_show_menu_uses_one_based_index(self, mock_print):
        choices = ["First", "Second"]

        show_menu(choices)

        calls = [call[0][0] for call in mock_print.call_args_list]
        self.assertIn("1. First", calls)
        self.assertIn("2. Second", calls)


class TestGetUserChoice(unittest.TestCase):
    @patch("builtins.input", side_effect=["2"])
    def test_get_user_choice_valid_input(self, mock_input):
        choices = ["Analyze", "Exit"]

        result = get_user_choice(choices)

        self.assertEqual(result, "Exit")
        mock_input.assert_called_once()

    @patch("builtins.input", side_effect=["3", "1"])
    def test_get_user_choice_invalid_then_valid(self, mock_input):
        choices = ["Analyze", "Exit"]

        result = get_user_choice(choices)

        self.assertEqual(result, "Analyze")
        self.assertEqual(mock_input.call_count, 2)

    @patch("builtins.print")
    @patch("builtins.input", side_effect=["abc", "1"])
    def test_get_user_choice_non_numeric_then_valid(self, mock_input, mock_print):
        choices = ["Analyze", "Exit"]

        result = get_user_choice(choices)

        self.assertEqual(result, "Analyze")
        self.assertTrue(mock_print.called)

    @patch("builtins.input", side_effect=["1"])
    def test_get_user_choice_single_choice(self, mock_input):
        choices = ["Only One"]

        result = get_user_choice(choices)

        self.assertEqual(result, "Only One")


class TestPromptRepoInput(unittest.TestCase):
    @patch("builtins.input", side_effect=["torvalds", "linux"])
    def test_prompt_repo_input_returns_tuple(self, mock_input):
        result = prompt_repo_input()

        self.assertIsInstance(result, tuple)
        self.assertEqual(result, ("torvalds", "linux"))
        self.assertEqual(mock_input.call_count, 2)

    @patch("builtins.input", side_effect=["  torvalds  ", "  linux  "])
    def test_prompt_repo_input_strips_whitespace(self, mock_input):
        result = prompt_repo_input()

        self.assertEqual(result, ("torvalds", "linux"))


class TestPromptReportFormat(unittest.TestCase):
    @patch("builtins.input", return_value="2")
    @patch("menu.show_menu")
    def test_prompt_report_format_returns_string(self, mock_show_menu, mock_input):
        result = prompt_report_format()

        self.assertEqual(result, "json")
        mock_show_menu.assert_called_once_with(["Text", "JSON"])
        mock_input.assert_called_once()

    @patch("builtins.input", return_value="1")
    @patch("menu.show_menu")
    def test_prompt_report_format_text(self, mock_show_menu, mock_input):
        result = prompt_report_format()

        self.assertEqual(result, "text")
        mock_show_menu.assert_called_once_with(["Text", "JSON"])


class TestConfirmExit(unittest.TestCase):
    @patch("builtins.input", return_value="y")
    def test_confirm_exit_with_y(self, mock_input):
        result = confirm_exit()
        self.assertTrue(result)

    @patch("builtins.input", return_value="yes")
    def test_confirm_exit_with_yes(self, mock_input):
        result = confirm_exit()
        self.assertTrue(result)

    @patch("builtins.input", return_value="n")
    def test_confirm_exit_with_n(self, mock_input):
        result = confirm_exit()
        self.assertFalse(result)

    @patch("builtins.input", return_value="no")
    def test_confirm_exit_with_no(self, mock_input):
        result = confirm_exit()
        self.assertFalse(result)

    @patch("builtins.input", return_value="anything")
    def test_confirm_exit_with_unexpected_input(self, mock_input):
        result = confirm_exit()
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
