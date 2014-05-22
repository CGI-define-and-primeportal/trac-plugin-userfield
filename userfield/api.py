from trac.core import Interface

class IUserFieldUser(Interface):
    """Extension point interface for components showing pages which
    need userfield fields.

    The genshi template should include HTML elements have class "user-field". 
    """

    def get_templates():
        """Yield template names"""

