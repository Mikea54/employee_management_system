from utils.incentives import Incentive, calculate_total_incentives


def test_calculate_total_incentives_all():
    incentives = [
        Incentive('bonus', 100),
        Incentive('commission', 50),
        Incentive('bonus', 25),
    ]
    assert calculate_total_incentives(incentives) == 175


def test_calculate_total_incentives_filtered():
    incentives = [
        Incentive('bonus', 100),
        Incentive('commission', 50),
        Incentive('bonus', 25),
    ]
    assert calculate_total_incentives(incentives, 'bonus') == 125
