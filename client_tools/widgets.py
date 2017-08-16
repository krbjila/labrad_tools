from PyQt4 import QtGui, QtCore, Qt
import numpy as np

class SuperSpinBox(QtGui.QLineEdit):
    def __init__(self, display_range, units, num_decimals=1, significant_figures=3):# num_decimals, display_factor=1):
        super(SuperSpinBox, self).__init__()
        self.display_range = display_range
        self.units = units
        self.display_factor = 10.**units[0][0] # display in units of display factor
        self.unit = units[0] # a string to be appended to the displayed value (e.g. 's')
        self.num_decimals = num_decimals # number of digits after decimal point to be displayed
        self.display(0)

    def keyPressEvent(self, c):
        if len(self.text().split('*')) > 1:
            print 'variable: ', self.text()
            super(SuperSpinBox, self).keyPressEvent(c)
            return
        if c.key() in [QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter]:
            split_text = self.text().split(' ')
            if len(split_text) == 1:
                unit = self.unit
            else:
                unit = self.text().split(' ')[1]
            if unit != self.unit: # see if the unit has been changed manually
                for f, u in self.units:
                    if unit == u:
                        self.unit = u
                        self.display_factor = 10.**f
            try:
                self.display(self.value())
            except: 
                self.display(0)
        super(SuperSpinBox, self).keyPressEvent(c)
        if c.key() == QtCore.Qt.Key_Up:
            self.step(up=1)
        if c.key() == QtCore.Qt.Key_Down:
            self.step(up=0)

    def step(self, up):
        """ if we press the up (down) key, increment (decrement) the digit to the left of the cursor by one"""
        text = self.text().split(' ')[0] # previously displayed value, strip away unit
        cursor_position = self.cursorPosition() # position, from left, of cursor
        decimal_position = len(text.split('.')[0]) +1 #position, from left, of decimal
        rel_position = decimal_position - cursor_position # how far is the cursor from the decimal point
        if cursor_position < decimal_position: # cursor immedeately on either side of decimal is equivalent
            rel_position -= 1
        
        value = float(text)*self.display_factor # what is this in units of display factor = 1?
        step_size = 10.**rel_position*self.display_factor # step by one in the digit to the left of cursor
        if up: # if we press the up key, increment the digit to the left of the cursor by one
            self.display(value + step_size)
        else: # if we press the down key decrement the digit to the left of the cursor by one
            self.display(value - step_size)
        self.returnPressed.emit()

    def display(self, value):
	if str(value)[0] == '*':
            self.setText(value)
	    return
        text = self.text().split(' ')[0] # previously displayed value, strip away unit
        cursor_position = self.cursorPosition() # position, from left, of cursor
        decimal_position = len(text.split('.')[0]) +1 #position, from left, of decimal
        rel_position = decimal_position - cursor_position # how far is the cursor from the decimal point
        if cursor_position < decimal_position: # cursor immedeately on either side of decimal is equivalent
            rel_position -= 1

        value = sorted([self.display_range[0], value, self.display_range[1]])[1] # force value to be within [min, max]
        self.display_factor, self.unit = self.format_number(value)        
        self.setText(str('{:0.'+str(self.num_decimals)+'f}' + ' {}'.format(self.unit)).format(value/self.display_factor))
        # place cursor in previous place 
        decimal_position = len(self.text().split('.')[0]) +1
        cursor_position = decimal_position - rel_position
        if rel_position >= 0:
            cursor_position -= 1
        self.setCursorPosition(cursor_position)

    def format_number(self, value):
        """ take a number and express it in most appropriate units"""
        def log10(x):
            if x != 0:
                return np.log10(abs(x))
            else: 
                return float(2**64-1)
        factor = min(zip(*self.units)[0], key=lambda x: abs(x-np.floor(log10(value))+1))
        for x, y in self.units:
            if x == factor:
                return 10.**x, y

    def value(self):
        text = self.text()
        if text[0] == '*':
            return str(text.replace(' ', ''))
        else:
            return float(self.text().split(' ')[0])*self.display_factor

class NeatSpinBox(QtGui.QLineEdit):
    def __init__(self):
        super(NeatSpinBox, self).__init__()
        self.display(0, True)
        self.setText('')
    
    def keyPressEvent(self, c):
        super(NeatSpinBox, self).keyPressEvent(c)
        if c.key() == QtCore.Qt.Key_Up:
            self.step(up=1)
        if c.key() == QtCore.Qt.Key_Down:
            self.step(up=0)

    def display(self, value, overwrite=False):
        print self.hasFocus()
        if overwrite or not self.hasFocus():
            # keep previously displayed value
            text = self.text()
            
            # position, from left, of cursor
            cursorPosition = self.cursorPosition() 
            
            #position, from left, of decimal
            try:
                decimalPosition = len(text.split('.')[0]) +1
            except IndexError:
                decimalPosition = len(text)+1
            
            # how far is the cursor from the decimal point
            relPosition = decimalPosition - cursorPosition 
            
            # cursor immedeately on either side of decimal is equivalent
            if cursorPosition < decimalPosition: 
                relPosition -= 1
            
            self.setText(str(value))
            # place cursor in previous place 
            decimalPosition = len(self.text().split('.')[0]) +1
            cursorPosition = decimalPosition - relPosition
            if relPosition >= 0:
                cursorPosition -= 1
            self.setCursorPosition(cursorPosition)

    def step(self, up):
        """ if we press the up (down) key, increment (decrement) the digit to the left of the cursor by one"""
        # keep previously displayed value
        text = self.text().split(' ')[0] 
       
        # position, from left, of cursor
        cursorPosition = self.cursorPosition() 
    
        #position, from left, of decimal
        try:
            decimalPosition = len(text.split('.')[0]) +1
        except IndexError:
            decimalPosition = len(text)+1
       
        # how far is the cursor from the decimal point
        relPosition = decimalPosition - cursorPosition 
       
        # cursor immedeately on either side of decimal is equivalent
        if cursorPosition < decimalPosition: 
            relPosition -= 1
        value = float(text)

        # step by one in the digit to the left of cursor
        step_size = 10.**relPosition 

        # if we press the up (down) key, increase (decrease) the digit to the left of the cursor by one
        if up: 
            self.display(value + step_size, True)
        else:
            self.display(value - step_size, True)

        self.returnPressed.emit()

    def value(self):
        return float(self.text().split(' ')[0])
        
class IntSpinBox(QtGui.QLineEdit):
    def __init__(self, displayRange):
        self.displayRange = displayRange
        super(IntSpinBox, self).__init__()
        self.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        self.display(0, True)
    
    def keyPressEvent(self, c):
        super(IntSpinBox, self).keyPressEvent(c)
        if c.key() == QtCore.Qt.Key_Up:
            self.step(up=1)
        if c.key() == QtCore.Qt.Key_Down:
            self.step(up=0)

    def display(self, value, overwrite=False):
        if overwrite or not self.hasFocus():
            # position, from right, of cursor
            cursorPositionR = len(self.text()) - self.cursorPosition() 
            value = sorted([min(self.displayRange), value, max(self.displayRange)])[1]
            self.setText(str(int(value)))
            # place cursor in previous place 
            self.setCursorPosition(len(self.text()) - cursorPositionR)

    def step(self, up):
        """ if we press the up (down) key, increment (decrement) the digit to the left of the cursor by one"""
        # keep previously displayed value
        text = self.text().split(' ')[0] 
        value = int(text)

        # position, from right, of cursor
        cursorPositionR = len(self.text()) - self.cursorPosition() 
    
        # step by one in the digit to the left of cursor
        step_size = 10.**cursorPositionR

        # if we press the up (down) key, increase (decrease) the digit to the left of the cursor by one
        if up: 
            self.display(value + step_size, True)
        else:
            self.display(value - step_size, True)

        self.returnPressed.emit()

    def value(self):
        return float(self.text().split(' ')[0])

if __name__ == '__main__':
    a = QtGui.QApplication([])
    import qt4reactor 
    qt4reactor.install()
    from twisted.internet import reactor
    widget = IntSpinBox([-100, 100])
    widget.show()
    reactor.run()
