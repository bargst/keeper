# This file is part of Maker Keeper Framework.
#
# Copyright (C) 2018 reverendus, bargst
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import pytest
from pymaker.dss import Collateral

from web3 import HTTPProvider
from web3 import Web3

from pymaker import Address, Wad, Contract
from pymaker.approval import directly
from pymaker.auctions import Flipper, Flapper, Flopper
from pymaker.auth import DSGuard
from pymaker.deployment import DssDeployment
from pymaker.numeric import Ray
from pymaker.token import DSToken

from tests.helpers import time_travel_by, snapshot, reset


@pytest.fixture(scope="session")
def web3():
    web3 = Web3(HTTPProvider("http://localhost:8555"))
    web3.eth.defaultAccount = web3.eth.accounts[0]
    return web3

@pytest.fixture(scope="session")
def d(web3):
    deployment = DssDeployment.deploy(web3=web3, debt_ceiling=Wad.from_number(1000000))
    for c in deployment.collaterals:
        assert c.gem.mint(Wad.from_number(1000)).transact()
    return deployment


@pytest.fixture(scope="session")
def dai(d: DssDeployment):
    return d.dai


@pytest.fixture(scope="session")
def c(d: DssDeployment):
    return d.collaterals[0]


@pytest.fixture(scope="session")
def gem(c: Collateral):
    return c.gem


@pytest.fixture(scope="session")
def flipper(c: Collateral):
    return c.flipper


class TestFlipper:
    # def setup_method(self):
    #     self.web3 = Web3(HTTPProvider("http://localhost:8555"))
    #     self.web3.eth.defaultAccount = self.web3.eth.accounts[0]
    #     self.our_address = Address(self.web3.eth.defaultAccount)
    #     self.other_address_1 = Address(self.web3.eth.accounts[1])
    #     self.other_address_2 = Address(self.web3.eth.accounts[2])
    #
    #     self.dai = DSToken.deploy(self.web3, 'DAI')
    #
    #     # we need a GemLike version of DSToken with push(bytes32, uint function)
    #     self.gem_addr = Contract._deploy(self.web3, Contract._load_abi(__name__, 'abi/GemMock.abi'), Contract._load_bin(__name__, 'abi/GemMock.bin'), [b'ABC'])
    #     self.gem = DSToken(web3=self.web3, address=self.gem_addr)
    #
    #     self.flipper = Flipper.deploy(self.web3, self.dai.address, self.gem.address)
    #
    #     # Set allowance to allow flipper to move dai and gem
    #     # With full deployment kick is only done by Cat via flip() which take care of allowance via gem.hope()
    #     self.gem.approve(self.flipper.address).transact()
    #     self.gem.approve(self.flipper.address).transact(from_address=self.other_address_1)
    #     self.dai.approve(self.flipper.address).transact()

    def test_era(self, flipper):
        assert flipper.era() > 1000000

    def test_beg(self, flipper):
        assert flipper.beg() == Ray.from_number(1.05)

    def test_ttl(self, flipper):
        assert flipper.ttl() == 3*60*60  # 3 hours

    def test_tau(self, flipper):
        assert flipper.tau() == 2*24*60*60  # 2 days

    def test_read(self, web3, gem: DSToken, flipper):
        # given
        our_address = Address(web3.eth.accounts[0])
        other_address_1 = Address(web3.eth.accounts[1])
        other_address_2 = Address(web3.eth.accounts[2])

        assert gem.mint(Wad.from_number(100)).transact()
        assert gem.balance_of(our_address) >= Wad.from_number(100)

        # when
        assert flipper.kick(urn=other_address_1,
                            gal=other_address_2,
                            tab=Wad.from_number(5000),
                            lot=Wad.from_number(100),
                            bid=Wad.from_number(100)).transact()

        # then
        assert flipper.kicks() == 1
        # and
        auction = flipper.bids(1)
        assert auction.lad == other_address_1
        assert auction.gal == other_address_2
        assert auction.bid == Wad.from_number(100)
        assert auction.lot == Wad.from_number(100)
        assert auction.tab == Wad.from_number(5000)
        assert auction.guy == our_address
        assert auction.tic == 0
        assert auction.end > 0

    def test_scenario(self, web3, gem: DSToken, dai: DSToken, flipper):
        # given
        our_address = Address(web3.eth.accounts[0])
        other_address_1 = Address(web3.eth.accounts[1])

        assert dai.mint(Wad.from_number(100000)).transact()
        assert gem.mint(Wad.from_number(100)).transact()
        assert gem.transfer(other_address_1, Wad.from_number(100)).transact()
        assert dai.balance_of(our_address) == Wad.from_number(100000)

        # when
        flipper.kick(urn=other_address_1,
                     gal=other_address_1,
                     tab=Wad.from_number(5000),
                     lot=Wad.from_number(100),
                     bid=Wad.from_number(1000)).transact(from_address=other_address_1)
        # then
        assert dai.balance_of(our_address) == Wad.from_number(100000)
        assert dai.balance_of(other_address_1) == Wad.from_number(0)
        assert gem.balance_of(our_address) == Wad.from_number(0)
        assert gem.balance_of(other_address_1) == Wad.from_number(0)

        # when
        flipper.tend(1, Wad.from_number(100), Wad.from_number(2000)).transact()
        assert dai.balance_of(our_address) == Wad.from_number(100000) - Wad.from_number(2000)
        assert dai.balance_of(other_address_1) == Wad.from_number(2000)
        assert gem.balance_of(our_address) == Wad.from_number(0)
        assert gem.balance_of(other_address_1) == Wad.from_number(0)

        # when
        flipper.tend(1, Wad.from_number(100), Wad.from_number(5000)).transact()
        assert dai.balance_of(our_address) == Wad.from_number(100000) - Wad.from_number(5000)
        assert dai.balance_of(other_address_1) == Wad.from_number(5000)
        assert gem.balance_of(our_address) == Wad.from_number(0)
        assert gem.balance_of(other_address_1) == Wad.from_number(0)

        # when
        flipper.dent(1, Wad.from_number(80), Wad.from_number(5000)).transact()
        assert dai.balance_of(our_address) == Wad.from_number(100000) - Wad.from_number(5000)
        assert dai.balance_of(other_address_1) == Wad.from_number(5000)
        assert gem.balance_of(our_address) == Wad.from_number(0)
        assert gem.balance_of(other_address_1) == Wad.from_number(20)

        time_travel_by(web3, 60*60*24*8)

        # when
        flipper.deal(1).transact()
        assert dai.balance_of(our_address) == Wad.from_number(100000) - Wad.from_number(5000)
        assert dai.balance_of(other_address_1) == Wad.from_number(5000)
        assert gem.balance_of(our_address) == Wad.from_number(80)
        assert gem.balance_of(other_address_1) == Wad.from_number(20)


class TestFlapper:
    def setup_method(self):
        self.web3 = Web3(HTTPProvider("http://localhost:8555"))
        self.web3.eth.defaultAccount = self.web3.eth.accounts[0]
        self.our_address = Address(self.web3.eth.defaultAccount)
        self.dai = DSToken.deploy(self.web3, 'DAI')
        self.gem = DSToken.deploy(self.web3, 'MKR')
        self.flapper = Flapper.deploy(self.web3, self.dai.address, self.gem.address)

    def test_era(self):
        assert self.flapper.era() > 1000000

    def test_dai(self):
        assert self.flapper.dai() == self.dai.address

    def test_gem(self):
        assert self.flapper.gem() == self.gem.address

    def test_beg(self):
        assert self.flapper.beg() == Ray.from_number(1.05)

    def test_ttl(self):
        assert self.flapper.ttl() == 3*60*60

    def test_tau(self):
        assert self.flapper.tau() == 2*24*60*60

    def test_read(self):
        # given
        pit = Address(self.web3.eth.accounts[1])
        # and
        self.dai.mint(Wad.from_number(50000000)).transact()
        self.gem.mint(Wad.from_number(1000)).transact()

        # expect
        assert self.flapper.kicks() == 0

        # when
        self.dai.approve(self.flapper.address).transact()
        self.flapper.kick(pit, Wad.from_number(20000), Wad.from_number(1)).transact()
        # then
        assert self.flapper.kicks() == 1
        # and
        auction = self.flapper.bids(1)
        assert auction.bid == Wad.from_number(1)
        assert auction.lot == Wad.from_number(20000)
        assert auction.guy == self.our_address
        assert auction.tic == 0
        assert auction.end > 0

    def test_scenario(self):
        # given
        pit = Address(self.web3.eth.accounts[1])
        # and
        self.dai.mint(Wad.from_number(50000000)).transact()
        self.gem.mint(Wad.from_number(1000)).transact()

        # when
        self.dai.approve(self.flapper.address).transact()
        self.flapper.kick(pit, Wad.from_number(20000), Wad.from_number(1)).transact()
        # then
        assert self.dai.balance_of(self.our_address) == Wad.from_number(49980000)
        assert self.gem.balance_of(pit) == Wad.from_number(0)
        # and
        assert self.flapper.bids(1).tic == 0

        self.flapper.approve(directly())

        # when
        self.flapper.tend(1, Wad.from_number(20000), Wad.from_number(1.5)).transact()
        # then
        assert self.dai.balance_of(self.our_address) == Wad.from_number(49980000)
        assert self.gem.balance_of(pit) == Wad.from_number(0.5)
        # and
        assert self.flapper.bids(1).tic > 0

        # when
        self.flapper.tend(1, Wad.from_number(20000), Wad.from_number(2.0)).transact()
        # then
        assert self.dai.balance_of(self.our_address) == Wad.from_number(49980000)
        assert self.gem.balance_of(pit) == Wad.from_number(1.0)
        # and
        assert self.flapper.bids(1).tic > 0

        time_travel_by(self.web3, 60*60*24*8)

        # when
        self.flapper.deal(1).transact()
        # then
        # assert self.dai.balance_of(self.our_address) == Wad.from_number(50000000)
        assert self.gem.balance_of(pit) == Wad.from_number(1.0)


class TestFlopper:
    def setup_method(self):
        self.web3 = Web3(HTTPProvider("http://localhost:8555"))
        self.web3.eth.defaultAccount = self.web3.eth.accounts[0]
        self.our_address = Address(self.web3.eth.defaultAccount)
        self.dai = DSToken.deploy(self.web3, 'DAI')
        self.gem = DSToken.deploy(self.web3, 'MKR')
        self.flopper = Flopper.deploy(self.web3, self.dai.address, self.gem.address)

        # so the Flopper can mint MKR
        dad = DSGuard.deploy(self.web3)
        dad.permit(self.flopper.address, self.gem.address, DSGuard.ANY).transact()
        self.gem.set_authority(dad.address).transact()

    def test_era(self):
        assert self.flopper.era() > 1000000

    def test_dai(self):
        assert self.flopper.dai() == self.dai.address

    def test_gem(self):
        assert self.flopper.gem() == self.gem.address

    def test_beg(self):
        assert self.flopper.beg() == Ray.from_number(1.05)

    def test_ttl(self):
        assert self.flopper.ttl() == 3*60*60

    def test_tau(self):
        assert self.flopper.tau() == 2*24*60*60

    def test_read(self):
        # given
        recidaint = Address(self.web3.eth.accounts[1])
        # and
        self.dai.mint(Wad.from_number(50000000)).transact()

        # expect
        assert self.flopper.kicks() == 0

        # when
        self.flopper.kick(recidaint, Wad.from_number(10), Wad.from_number(20000)).transact()
        # then
        assert self.flopper.kicks() == 1
        # and
        auction = self.flopper.bids(1)
        assert auction.bid == Wad.from_number(20000)
        assert auction.lot == Wad.from_number(10)
        assert auction.guy == recidaint
        assert auction.tic == 0
        assert auction.end > 0

    def test_scenario(self):
        # given
        recidaint = Address(self.web3.eth.accounts[1])
        # and
        self.dai.mint(Wad.from_number(50000000)).transact()

        # when
        self.flopper.kick(recidaint, Wad.from_number(10), Wad.from_number(20000)).transact()
        # then
        assert self.dai.balance_of(recidaint) == Wad(0)
        assert self.gem.total_supply() == Wad(0)
        # and
        assert self.flopper.bids(1).tic == 0

        self.flopper.approve(directly())

        # when
        self.flopper.dent(1, Wad.from_number(9), Wad.from_number(20000)).transact()
        # then
        assert self.dai.balance_of(recidaint) == Wad.from_number(20000)
        assert self.gem.total_supply() == Wad(0)
        # and
        assert self.flopper.bids(1).tic > 0

        # when
        self.flopper.dent(1, Wad.from_number(8), Wad.from_number(20000)).transact()
        # then
        assert self.dai.balance_of(recidaint) == Wad.from_number(20000)
        assert self.gem.total_supply() == Wad(0)
        # and
        assert self.flopper.bids(1).tic > 0

        time_travel_by(self.web3, 60*60*24*8)

        # when
        self.flopper.deal(1).transact()
        # then
        assert self.dai.balance_of(recidaint) == Wad.from_number(20000)
        assert self.gem.total_supply() == Wad.from_number(8)
