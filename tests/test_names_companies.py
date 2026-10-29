import unittest

from champion import companies, names


class Names(unittest.TestCase):
    def test_exact_ignores_case_and_spacing(self):
        self.assertEqual(names.compare("Robert  Chen", "robert chen"), "exact")

    def test_accents_are_the_same_letters(self):
        self.assertEqual(names.compare("José Pérez", "Jose Perez"), "exact")

    def test_nickname_either_way(self):
        self.assertEqual(names.compare("Robert Chen", "Bob Chen"), "variant")
        self.assertEqual(names.compare("Kate Byrne", "Katherine Byrne"), "variant")

    def test_less_common_nicknames(self):
        self.assertEqual(names.compare("Rebecca Thornbury", "Becky Thornbury"), "variant")
        self.assertEqual(names.compare("Richard Hale", "Dick Hale"), "variant")

    def test_two_nicknames_of_one_name(self):
        self.assertEqual(names.compare("Bob Chen", "Rob Chen"), "variant")

    def test_middle_name_and_hyphenated_surname(self):
        self.assertEqual(names.compare("Robert J. Chen", "Robert Chen"), "variant")
        self.assertEqual(names.compare("Lucía Fernández-Ortiz", "Lucia Fernandez"), "variant")

    def test_family_name_first(self):
        self.assertEqual(names.compare("Wei Zhang", "Zhang Wei"), "variant")

    def test_initial_only(self):
        self.assertEqual(names.compare("Ngozi Eze", "N. Eze"), "initial")

    def test_punctuation_and_joined_words(self):
        self.assertEqual(names.compare("Mary-Kate O'Donnell", "Marykate ODonnell"), "variant")

    def test_two_spellings_of_one_first_name(self):
        self.assertEqual(names.compare("Yevgenia Kharitonova", "Evgeniya Kharitonova"), "spelling")
        self.assertEqual(names.compare("Aleksandr Petrov", "Alexander Petrov"), "spelling")
        self.assertEqual(names.compare("Sergei Ivanov", "Sergey Ivanov"), "spelling")

    def test_short_form_of_a_first_name_is_weak(self):
        self.assertEqual(names.compare("Oluwaseun Adeyemi", "Seun Adeyemi"), "spelling")
        self.assertEqual(names.compare("Al Grant", "Alan Grant"), "variant")  # in the table
        self.assertEqual(names.compare("Jo Grant", "Joanna Grant"), "different")  # too short to guess

    def test_shared_initial_or_prefix_is_not_a_shared_surname(self):
        self.assertEqual(names.compare("Robert J. Chen", "Robert J. Lee"), "different")
        self.assertEqual(names.compare("Liam O'Brien", "Liam O'Neill"), "different")
        self.assertEqual(names.compare("Robert James Chen", "Robert James Lee"), "different")

    def test_mac_and_mc_are_one_surname(self):
        self.assertEqual(names.compare("Fiona MacAllister", "Fiona McAllister"), "exact")

    def test_surname_spelled_another_way_is_weak(self):
        self.assertEqual(names.compare("Yevgeniya Shcherbinina", "Evgenia Scherbinina"), "spelling")
        self.assertEqual(names.compare("Anna Shcherbinina", "Anna Scherbinina"), "spelling")
        self.assertEqual(names.compare("Wei Chen", "Wei Chan"), "different")  # too short to guess

    def test_different_surname_or_first_name(self):
        self.assertEqual(names.compare("Anna Novak", "Anna Kowalski"), "different")
        self.assertEqual(names.compare("Michael Grant", "Mitchell Grant"), "different")
        self.assertEqual(names.compare("", "Anna Novak"), "different")

    def test_first_names_agree_ignores_surname(self):
        self.assertTrue(names.first_names_agree("Fatima Haddad", "Fatima Rahman"))
        self.assertTrue(names.first_names_agree("Elizabeth Ward", "Liz Moore"))
        self.assertFalse(names.first_names_agree("Michael Grant", "Mitchell Grant"))


class Companies(unittest.TestCase):
    def test_suffixes_and_the_are_ignored(self):
        self.assertTrue(companies.same("The Proseware Company", "Proseware"))
        self.assertTrue(companies.same("Litware Inc.", "litware"))
        self.assertTrue(companies.same("Quillon Ltd", "Quillon"))

    def test_dotted_and_more_legal_suffixes(self):
        self.assertTrue(companies.same("Shirakawa Precision K.K.", "Shirakawa Precision"))
        self.assertTrue(companies.same("Harlan and Pryce LLP", "Harlan & Pryce"))

    def test_different_companies_stay_different(self):
        self.assertFalse(companies.same("Contoso", "Contoso Travel"))
        self.assertFalse(companies.same("Inc.", "Ltd"))  # nothing left after the suffixes

    def test_rename_needs_the_alias(self):
        self.assertFalse(companies.same("Trey Research", "Treyline"))
        groups = companies.alias_groups([("Trey Research", "Treyline")])
        self.assertTrue(companies.same("Trey Research", "Treyline", groups))
        self.assertTrue(companies.same("Treyline Ltd", "Trey Research", groups))

    def test_alias_chains_join(self):
        groups = companies.alias_groups([("Adatum", "Adatum Labs"), ("Adatum Labs", "Datum One")])
        self.assertTrue(companies.same("Adatum", "Datum One", groups))
        self.assertFalse(companies.same("Adatum", "Contoso", groups))


if __name__ == "__main__":
    unittest.main()
