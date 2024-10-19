let number = 0
radio.onReceivedNumber(function (receivedNumber) {
    basic.showNumber(receivedNumber)
})
input.onGesture(Gesture.Shake, function () {
    radio.setGroup(210)
    number = randint(0, 6)
    basic.showNumber(number)
    radio.sendNumber(number)
})
basic.forever(function () {
	
})
