// See priceOracleReport.md for a detailed description of these rules.

methods {
    // lifecycle management ////////////////////////////////////////////////////

    /* initialize(t) succeeds iff
        - state is not initialized 
        - t is either 1 week or 1 day */
    /* initialize(t) has the following side effects:
        - state becomes initialized
        - owner is set to msg.sender
        - dateOffset is set to t */
    initialize(uint256) 

    /* addTokenPair(u,c,o) succeeds iff
        - state is initialized
        - caller is the owner
        - oracles(u,c) is undefined
        - o is nonzero
        */
    /* addTokenPair(u,c,o) has the following side effects:
        - oracles(u,c) is set to o
        */
    addTokenPair(address, address, address) 

    // settlement price management /////////////////////////////////////////////

    /* setSettlementPrice(u,c) succeeds if
        - oracles(u,c) is defined
        - oracles(u,c).latestData() succeeds
        - request has sufficient gas to reestablish invariants */
    /* setSettlementPrice(u,c) has the following effects:
        - updates price(u,c,timestamp) = oracles(u,c).latestData()
        - may update price(u,c,t') for other t' in order to maintain invariants
        */
    setSettlementPrice(address,address) 

    /* succeeds if date is an epoch boundary */
    /* updates price(u,c,t) if price(u,c,t) is 0 */
    setSettlementPriceForDate(address,address,uint256)

     // getters / helper functions //////////////////////////////////////////////

    /* always succeeds.  Returns (price(u,c,t) != 0, price(u,c,t)) */
    getSettlementPrice(address,address,uint256)
        returns (bool, uint256)

    /* getCurrentPrice(u, c) succeeds if:
        - an oracle exists for the given pair
       getCurrentPrice(u, c) has the following effects:
        - returns a boolean if the price is 0
        - returns the price listed by an oracle for a given u and c
    */
    getCurrentPrice(address, address)
        returns (uint256)

    /* always succeeds.  Returns the largest epoch boundary before t */
    get8amWeeklyOrDailyAligned(uint256)
        returns (uint256) 

    /* getters generated by solidity */
    settlementPrices(address, address, uint256) returns (uint256) envfree
    dateOffset() returns (uint256) envfree
    oracles(address,address) returns (address) envfree //fixed on review (added return)
    owner() envfree
    _initialized() returns (bool) envfree // fixed on review changed variable to public and added getter 
    _initializing() returns (bool) envfree // fixed on review changed variable to public and added getter

    /* getters implemented by harness */
    getOracleAnswer(address, address) returns (int256) envfree
    answer() returns (int256)  => DISPATCHER(true)

    // external method specifications //////////////////////////////////////////

    latestRoundData() => DISPATCHER(true)
    // latestRoundData() => NONDET
    // latestRoundData() => ALWAYS(2)
}

//----------------------------- Ghosts -----------------------------------------
//
//

// NOTE: this whole section (and parts of the harness) should be removed once
//       the tool supports direct access of private fields within rules

/*
ghost initialized() returns bool;
ghost initializing() returns bool;

hook Sstore _initialized bool newvalue STORAGE {
  // NOTE: this logic is required because having a hook with type bool seems to not
  //       currently work.  Similarly for other hooks below
  // NOTE: optimization breaks this because _initialized shares a slot
  // taking the rightmost 8 bits of the newly recored value
  uint normNewValue = newvalue & 0xff;
  bool boolNewValue = normNewValue > 0;
  havoc initialized assuming initialized@new() == boolNewValue;
}

hook Sload bool newvalue _initialized STORAGE {
  require (newvalue & 0xff > 0) == initialized();
}

hook Sstore _initializing bool newvalue STORAGE {
  uint normNewValue = newvalue & 0xff;
  bool boolNewValue = normNewValue > 0;
  havoc initializing assuming initializing@new() == boolNewValue;
}

hook Sload bool newvalue _initializing STORAGE {
  require (newvalue & 0xff > 0) == initializing();
}
*/

definition uninitialized() returns bool =
  !_initialized();


//---------------------------- Definitions -------------------------------------
//
//


// placeholders since CVT doesn't seem to support solidity's hour / day keywords

definition oneMinute() returns uint256 = 60;
definition oneHour()   returns uint256 = 60 * oneMinute();
definition oneDay()    returns uint256 = 24 * oneHour();
definition oneWeek()   returns uint256 = 7  * oneDay();
definition MAX_DATE()   returns uint256 = 100000000000000000000000000000000000000000000000;
definition time_bounded(uint256 t) returns bool = t < MAX_DATE() && t > dateOffset();
                                         

// definition isEpochBoundary(uint256 timestamp) returns bool =
//   dateOffset() != 0 && // If date offset is 0, then there are no epoch boundaries
//   (dateOffset() == oneDay()
//     ? timestamp % oneDay()  == 8 * oneHour() // 8 am of the given day
//     : timestamp % oneWeek() == oneDay() + 8 * oneHour()  // 8 am friday
//   )
// ;

// This is just a shorthand for convenience
definition _price(address u, address c, uint256 t) returns uint256 =
  settlementPrices(u,c,t);


//---------------------------Invariants----------------------------------------
//
//

// initialization
// @MM - Make sense - checks that the contract is not ever in initialization process.
invariant noninitializing() 
  !_initializing()

// @MM - Make sense - checks that if dateOffset is 0 then the contract is uninitiallized, then check
invariant dateOffset_initialization()
  dateOffset() == 0 <=> uninitialized()
  { preserved { requireInvariant noninitializing(); } }

// @MM - Make sense - since owner is initialized only in "initialize" function,
// if owner is 0 then there was no initialization. Also, if the instance was uninitialized then the owner has to be 0 (no owner).
// It makes sure that it is not in initializing process (initializing == true)
invariant owner_initialization()
  owner() == 0 <=> uninitialized()
    { preserved { requireInvariant noninitializing(); }
    preserved initialize(uint256 offset) with (env e) {
      requireInvariant noninitializing();
      require e.msg.sender != 0;
    }
  }

// add dateOffset_initialization()
// @MM - Make sense - if the instance is uninitialized then all prices should be 0.
// We require that the instace won't be in the process of initialization. 
invariant price_initialization(address u, address c, uint256 t)
  uninitialized() => _price(u,c,t) == 0
  { preserved { requireInvariant noninitializing(); 
            requireInvariant dateOffset_initialization(); } }

// @MM - Make sense - if the instance is uninitialized then the oracle should be of value 0 (default - no oracle)
invariant oracles_initialization(address u, address c)
  uninitialized() => oracles(u,c) == 0
  // @MM - Q: What is this needed for?
  { preserved addTokenPair(address _u, address _c, address _o) with (env e) {
      requireInvariant owner_initialization();
      require e.msg.sender != 0;
    }
  }

// an execution of 3 noninitialization.
function requireInitializationInvariants() {
  requireInvariant noninitializing();
  requireInvariant dateOffset_initialization();
  requireInvariant owner_initialization();
}

// dateOffset

// Do we want to allow dateOffset to be 1day or 1week on constructor?
invariant dateOffset_value()
  dateOffset() == 0 || dateOffset() == oneDay() || dateOffset() == oneWeek()

// price

invariant price_domain(address u, address c, uint256 t)
  _price(u,c,t) != 0 => oracles(u,c) != 0

// Note: This times out and as such is covered by the rule oracle_price_nontrivial
// invariant price_nontrivial(address u, address c)
//   oracles(u,c) != 0 => (exists uint256 t. _price(u,c,t) != 0)

// @MM - I think a stronger rule than the original will be that the t1-t2 = dateOffset()*const
invariant price_spacing(address u, address c, uint256 t1, uint256 t2)//, uint256 const)
  _price(u,c,t1) != 0 && _price(u,c,t2) != 0 && t1 > t2 =>
  ( t1 - t2 >= dateOffset() || t2 - t1 >= dateOffset() ) 
  //(dateOffset() != 0 && ((t1 - t2) % dateOffset()) == 0)//((t1 - t2) / dateOffset()) * dateOffset() == (t1 - t2))
  { preserved {
    requireInitializationInvariants();
    requireInvariant price_initialization(u,c,t1);
    requireInvariant price_initialization(u,c,t2); 
  } }

/*
rule price_space(address u, address c, uint256 t1, uint256 t2)
{
  requireInitializationInvariants();

}
*/

// faiing in add token pair due to a combination of prize initialize to 0 bug and arbitrary state states being non-zero
invariant price_compact_right(address u, address c, uint256 t0, uint256 t)
  _price(u,c,t0) != 0 && _price(u,c, to_uint256(t0 + dateOffset())) == 0 =>
    (t > t0 => _price(u,c,t) == 0)
    { preserved {
        requireInitializationInvariants(); 
        requireInvariant price_domain(u, c, t);
        requireInvariant price_domain(u, c, t0);
        requireInvariant price_initialization(u,c,t0);
        requireInvariant price_initialization(u,c,t); 
        requireInvariant dateOffset_value();
        require time_bounded(t);
        require time_bounded(t0);
    } }

invariant price_compact_left(address u, address c, uint256 t0, uint256 t)
  _price(u,c,t0) != 0 && _price(u,c,to_uint256(t0 - dateOffset())) == 0 =>
    (t < t0 => _price(u,c,t) == 0)
    { preserved {
        requireInitializationInvariants();         
        requireInvariant price_domain(u, c, t);
        requireInvariant price_domain(u, c, t0);
        requireInvariant price_initialization(u,c,t0);
        requireInvariant price_initialization(u,c,t);
        requireInvariant dateOffset_value(); 
        require time_bounded(t);
        require time_bounded(t0);
    } }

// These invariants are not checked because of timeouts, but
// should be covered by the spacing and compactness requirements
// 
// invariant price_convex (address u, address c, uint256 t1, uint256 t2)
//   _price(u,c,t1) != 0 && _price(u,c,t2) != 0 =>
//   (forall uint256 t.
//     t1 <= t && t <= t2 && isEpochBoundary(t) => _price(u,c,t) != 0)
//
// invariant price_domain_epoch(address u, address c, uint256 t)
//   _price(u,c,t) != 0 => isEpochBoundary(t)



//---------------------------Owner transitions---------------------------------
//
//

rule owner_initialize_only(method f) {
  env e; calldataarg args;

  address ownerBefore = owner();
  f(e,args);
  address ownerAfter  = owner();

  assert ownerBefore != ownerAfter =>
    f.selector == initialize(uint256).selector,
    "owner is only changed by initialize";

  assert ownerBefore != ownerAfter =>
    ownerAfter == e.msg.sender,
    "owner is changed to the intialize(..) message sender";
}

rule owner_single_definition(method f) {
  env e; calldataarg args;

  requireInitializationInvariants();

  bool uninitBefore = uninitialized();
  address ownerBefore = owner();
  f(e,args);
  address ownerAfter  = owner();

  assert ownerBefore != ownerAfter =>
    uninitBefore,
    "owner can only be changed if uninitialized";
}

//---------------------------dateOffset transitions----------------------------
//
//

rule dateOffset_transition (method f) {
  env e; calldataarg args;

  uint256 dateOffsetBefore = dateOffset();
  f(e, args);
  uint256 dateOffsetAfter  = dateOffset();

  assert dateOffsetBefore != dateOffsetAfter =>
    f.selector == initialize(uint256).selector,
    "dateOffset only changed by initialize";

  // NOTE: argument to initialize checked in rule dateOffset_transition_initialize below
}

rule dateOffset_transition_initialize() {
  env e;
  uint256 date;

  initialize(e, date);

  assert dateOffset() == date,
    "dateOffset changed to d by initialize(d)";
}

rule dateOffset_single_definition(method f) {
  env e; calldataarg args;

  requireInitializationInvariants();

  uint256 dateOffsetBefore = dateOffset();
  f(e, args);
  uint256 dateOffsetAfter  = dateOffset();

  assert dateOffsetBefore != dateOffsetAfter =>
    dateOffsetBefore == 0,
    "dataOffset only changed if undefined";
}

//-------------------------Oracle Changes-----------------------------
//
//

rule oracle_valid_change (method f) {
  env e;
  calldataarg arg;

  address underlying; address currency;

  address oracleBefore = oracles(underlying, currency);
  f(e, arg);
  address oracleAfter  = oracles(underlying, currency);

  assert oracleBefore != oracleAfter =>
    f.selector == addTokenPair(address,address,address).selector,
    // NOTE: arguments to addTokenPair are handled by oracle_transition_addTokenPair below
    "only addTokenPair can change the oracle";
}

rule oracle_transition_addTokenPair() {
  env e;
  address underlying; address currency; address newOracle;

  address oracleBefore = oracles(underlying, currency);

  address call_u; address call_c;
  addTokenPair(e, call_u, call_c, newOracle);

  address oracleAfter  = oracles(underlying, currency);

  assert oracleAfter != oracleBefore =>
    underlying == call_u && currency == call_c && oracleAfter == newOracle,
    "addTokenPair may only change the oracle given by its arguments";
}

rule oracle_owner_only (method f) {
  env e;
  calldataarg arg;

  address underlying; address currency;

  address oracleBefore = oracles(underlying, currency);
  f(e, arg);
  address oracleAfter  = oracles(underlying, currency);

  assert oracleBefore != oracleAfter =>
    e.msg.sender == owner(),
    "only the contract owner can change an oracle";
}

rule oracle_single_definition (method f) {
  env e;
  calldataarg arg;

  address underlying; address currency;

  address oracleBefore = oracles(underlying, currency);
  f(e, arg);
  address oracleAfter  = oracles(underlying, currency);

  assert oracleBefore != oracleAfter =>
    oracleBefore == 0,
    "oracle can only be changed once";
}

// creating an oracle implies that the most recent price is set and alligned
rule oracle_price_nontrivial(method f) {
  env e;
  address u; address c; address a;
  calldataarg args;

  address oracle_before = oracles(u,c);
  f(e, args);
  address oracle_after = oracles(u,c);

  uint256 t = get8amWeeklyOrDailyAligned(e, e.block.timestamp);
  // _price is defined at the top. it is a getter of the exchage rate for a triplet in settelmentPrices.
  uint256 p = _price(u,c,t);
  // if the oracle of a token pair is changed due to function invocation
  assert oracle_before != oracle_after => p != 0, "oracle defined with no initial price";
}


//---------------------------------Price Evolution------------------------------------
//
//

rule price_single_edit (method f) {
  env e; calldataarg args;
  address u; address c; uint256 t;

  requireInvariant price_domain(u,c,t);

  uint256 priceBefore = _price(u,c,t);
  f(e, args);
  uint256 priceAfter  = _price(u,c,t);

  assert priceAfter != priceBefore =>
    priceBefore == 0,
    "price only changed if undefined";
}


rule price_accurate (method f) {
  env e; calldataarg args;
  address u; address c; uint256 t;
  requireInitializationInvariants();
  requireInvariant price_domain(u,c,t);
  uint256 priceBefore = _price(u,c,t);
  f(e, args);
  uint256 priceAfter  = _price(u,c,t);

  assert priceAfter != priceBefore =>
    to_mathint(priceAfter) == to_mathint(getOracleAnswer(u,c)),
    "check priceAfter is the result of a call to correct oracle";
}

rule price_bounded_past (method f) {
  env e; calldataarg args;
  address u; address c; uint256 t;

  uint256 priceBefore = _price(u,c,t);
  f(e, args);
  uint256 priceAfter  = _price(u,c,t);

  assert priceAfter != priceBefore =>
    t <= e.block.timestamp,
    "price only changed in the past";
}

// if a price is set, there is either a price set before that price or no price after set (indicating it is the first price)
// the first price is set by addTokenPair so this function is not relevant
rule price_t0_constant (method f) filtered {f -> (f.selector != addTokenPair(address, address, address).selector)}{
  uint256 t1; uint256 t;
  require t1 > t;

  env e; calldataarg args;
  address u; address c;

  uint256 p_before = _price(u,c,t);
  f(e, args);
  uint256 p_after = _price(u,c,t);

  assert p_before != p_after => _price(u,c,to_uint256(t - dateOffset())) != 0
                  || _price(u,c,t1) == 0, "value before prior values set";
}

/* Settlement Prices should only ever be changed by:
      - setSettlementPrice
      - setSettlementPriceForDate
      - addTokenPair
*/
rule price_authorized_only (method f) {
  env e; calldataarg args;
  address u; address c; uint256 t;
  
  uint256 p_before = _price(u,c,t);
  f(e,args);
  uint256 p_after = _price(u,c,t);

  assert p_before != p_after => f.selector == setSettlementPrice(address, address).selector ||
      f.selector == setSettlementPriceForDate(address, address, uint256).selector ||
      f.selector == addTokenPair(address, address, address).selector,
      "Unexpected function editing settlement prices";
}


//--------------------------------Unit Tests-----------------------------------
//
//

// get settlement price returns the accurate price, and returns t/f if nonzero/zero
rule verify_getSettlementPrice() {
  env e;
  address u; address c; uint256 t;

  uint256 ret_int; bool ret_bool;

  uint256 p_before = _price(u, c, t);

  ret_bool, ret_int = getSettlementPrice(e, u,c,t);

  uint256 p_after = _price(u, c, t);

  assert ret_int == _price(u,c,t), "Returned Wrong Value";
  assert ret_int != 0 <=> ret_bool, "boolean price mismatch";
  assert p_before == p_after, "price altered by viewing";
}

// if addTokenPair is called, a new oracle will be created
// no other oracles are changed when addTokenPair is called?
// if oracle(u, c) exists then add token pair will revert
rule verify_addTokenPair() {
  env e; 
  address u; address c; address o;
  require o > 0;
  address pre_val = oracles(u, c);
  address u1; address c1;
  address pre_alt_val = oracles(u1, c1);
  addTokenPair(e, u, c, o);

  // assert !initialized() => lastReverted, "addTokenPair did not revert but was not initialized";
  assert e.msg.sender != owner() => lastReverted, "caller other than owner did not revert";
  assert pre_val == 0 => oracles(u , c) == o, "Oracle was changed to incorrect address";
  assert pre_val != 0 => lastReverted, "already defined oracle changed";
  assert pre_alt_val != oracles(u1, c1) => u1 == u && c1 == c, "oracle at incorrect value changed";
}

rule verify_setSettlementPrice() {
  env e; 
  address u; address c; 
  uint256 t = get8amWeeklyOrDailyAligned(e, e.block.timestamp);
  uint256 p_pre = _price(u, c, t);
  setSettlementPrice(e, u, c);
  uint256 p_post = _price(u, c, t);
  uint256 price = getCurrentPrice(e, u, c);

  assert p_pre != p_post => oracles(u, c) != 0, "set for undefined oracle"; // oracles is defined
  assert p_pre != p_post => p_post == price, "incorrect price set"; // price is updated accurately
  assert p_pre != p_post => p_pre == 0, "price overwritten"; // price is only updated if 0
  // if conditions are correct, a settlement price will be set
  assert p_pre == 0 && oracles(u, c) != 0 && price != 0 => p_pre != p_post, "price not set";
  // assert p_pre == p_post => lastReverted, "price set failure"; // if price isn't updated the function reverted 
}

rule verify_setSettlementPriceForDate() {
  env e; 
  address u; address c; 
  uint256 t;
  uint256 p_pre = _price(u, c, t);
  setSettlementPrice(e, u, c);
  uint256 p_post = _price(u, c, t);
  uint256 price = getCurrentPrice(e, u, c);
  uint256 t_alligned = get8amWeeklyOrDailyAligned(e, t);

  assert p_pre != p_post => oracles(u, c) != 0, "set for undefined oracle"; // oracles is defined
  assert p_pre != p_post => p_post == price, "incorrect price set"; // price is updated accurately
  assert p_pre != p_post => p_pre == 0, "price overwritten"; // price is only updated if 0
  // assert p_pre == p_post => lastReverted, "price set failure"; // if price isn't updated the function reverted 
  assert p_pre != p_post => t ==t_alligned, "price set but not alligned"; // price must be alligned
  assert p_pre != p_post => t <= e.block.timestamp, "future price set"; // past prices only
  // long rule to assert that if the the necessary conditions are met, the price is set
  assert p_pre == 0 && oracles(u, c) != 0 && t == t_alligned && price != 0 => p_pre != p_post, "price not set";
}

rule verify_getCurrentPrice() {
  env e;
  address u; address c; uint256 t;

  uint256 p_before = _price(u, c, t);
  uint256 p = getCurrentPrice(e, u, c);
  uint256 p_after = _price(u, c, t);

  assert oracles(u, c) == 0 => lastReverted, "did not revert on an unset oracle";
  assert p_before == p_after, "price changed by viewing";
}
/*
rule sanity(method f) {
  env e;
  calldataarg args;
  f(e,args);
  assert false;
}*/