"""Birthday Paradox Simulation, by Al Sweigart al@inventwithpython.com
Explore the surprising probabilities of the "Birthday Paradox".
More info at https://en.wikipedia.org/wiki/Birthday_problem
View this code at https://nostarch.com/big-book-small-python-projects
Tags: short, math, simulation"""

import datetime
import random


def getBirthdays(numberOfBirthdays):
    """Returns a list of number random date objects for birthdays."""
    birthdays = []
    for i in range(numberOfBirthdays):
        # The year is unimportant for our simulation, as long as all
        # birthdays have the same year.
        startOfYear = datetime.date(2001, 1, 1)

        # Get a random day into the year:
        randomNumberOfDays = datetime.timedelta(random.randint(0, 364))
        birthday = startOfYear + randomNumberOfDays
        birthdays.append(birthday)
    return birthdays


def getMatch(birthdays):
    """Returns the date object of a birthday that occurs more than once
    in the birthdays list."""
    if len(birthdays) == len(set(birthdays)):
        return None  # All birthdays are unique, so return None.

    # Compare each birthday to every other birthday:
    for a, birthdayA in enumerate(birthdays):
        for b, birthdayB in enumerate(birthdays[a + 1:]):
            if birthdayA == birthdayB:
                return birthdayA  # Return the matching birthday.


def theoretical(n: int, days: int = 365) -> float:
    """Closed-form probability that any 2 of n people share a birthday.
    Computed as 1 - product_{k=0..n-1} (days-k)/days."""
    if n < 2:
        return 0.0
    if n > days:
        return 1.0
    p_unique = 1.0
    for k in range(n):
        p_unique *= (days - k) / days
    return 1.0 - p_unique


def wilson_ci(successes: int, trials: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score confidence interval. Default z=1.96 gives a 95% CI.
    More accurate than the normal-approximation interval, especially near 0/1."""
    if trials <= 0:
        return (0.0, 1.0)
    p = successes / trials
    n = trials
    denom = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / denom
    halfwidth = z * ((p * (1.0 - p) / n + z * z / (4.0 * n * n)) ** 0.5) / denom
    return (max(0.0, center - halfwidth), min(1.0, center + halfwidth))


def simulate(n: int, trials: int, rng=None, days: int = 365) -> int:
    """Run `trials` simulations of n random birthdays. Returns count of trials
    that contained at least one matching pair. Stdlib-only, set-based dedup."""
    if rng is None:
        rng = random
    matches = 0
    for _ in range(trials):
        bdays = [rng.randint(0, days - 1) for _ in range(n)]
        if len(set(bdays)) < n:
            matches += 1
    return matches


def main():
    # Display the intro:
    print('''Birthday Paradox, by Al Sweigart al@inventwithpython.com

The Birthday Paradox shows us that in a group of N people, the odds
that two of them have matching birthdays is surprisingly large.
This program does a Monte Carlo simulation (that is, repeated random
simulations) to explore this concept.

(It's not actually a paradox, it's just a surprising result.)
''')

    # Set up a tuple of month names in order:
    MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')

    while True:  # Keep asking until the user enters a valid amount.
        print('How many birthdays shall I generate? (Max 100)')
        response = input('> ')
        if response.isdecimal() and (0 < int(response) <= 100):
            numBDays = int(response)
            break  # User has entered a valid amount.
    print()

    # Generate and display the birthdays:
    print('Here are', numBDays, 'birthdays:')
    birthdays = getBirthdays(numBDays)
    for i, birthday in enumerate(birthdays):
        if i != 0:
            # Display a comma for each birthday after the first birthday.
            print(', ', end='')
        monthName = MONTHS[birthday.month - 1]
        dateText = '{} {}'.format(monthName, birthday.day)
        print(dateText, end='')
    print()
    print()

    # Determine if there are two birthdays that match.
    match = getMatch(birthdays)

    # Display the results:
    print('In this simulation, ', end='')
    if match != None:
        monthName = MONTHS[match.month - 1]
        dateText = '{} {}'.format(monthName, match.day)
        print('multiple people have a birthday on', dateText)
    else:
        print('there are no matching birthdays.')
    print()

    # Run through 100,000 simulations:
    print('Generating', numBDays, 'random birthdays 100,000 times...')
    input('Press Enter to begin...')

    print('Let\'s run another 100,000 simulations.')
    simMatch = 0  # How many simulations had matching birthdays in them.
    for i in range(100_000):
        # Report on the progress every 10,000 simulations:
        if i % 10_000 == 0:
            print(i, 'simulations run...')
        birthdays = getBirthdays(numBDays)
        if getMatch(birthdays) != None:
            simMatch = simMatch + 1
    print('100,000 simulations run.')

    # Display simulation results:
    probability = round(simMatch / 100_000 * 100, 2)
    print('Out of 100,000 simulations of', numBDays, 'people, there was a')
    print('matching birthday in that group', simMatch, 'times. This means')
    print('that', numBDays, 'people have a', probability, '% chance of')
    print('having a matching birthday in their group.')
    print('That\'s probably more than you would think!')


if __name__ == '__main__':
    main()
