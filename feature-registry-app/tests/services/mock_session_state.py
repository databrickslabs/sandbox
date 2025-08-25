from collections import UserDict

# Mock for st.session_state
class SessionStateMock(UserDict):
    def __getattr__(self, name):
        try:
            return self.data[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        if name == "data":
            super().__setattr__(name, value)
        else:
            self.data[name] = value
