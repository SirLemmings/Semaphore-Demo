import sqlite3


def update_alias(alias, pubkey):
    """
    Changes the pubkey associated with an alias in the database
    
    Parameters:
        alias (int): The alias to update
        pubkey (int):  The new public key to assign to the alias
    """
    con = sqlite3.connect("aliases.db")
    with con:
        cur = con.cursor()
        cur.execute(
            "UPDATE aliases SET pubkey = :new_pubkey WHERE alias = :alias",
            {"alias": alias, "new_pubkey": pubkey},
        )


def clear_alias(alias):
    """
    Removes the pubkey from an alias in the database
    
    Parameters:
        alias (int): The alias to remove the public key from
    """
    update_alias(alias, None)


def get_pubkey(alias):
    """
    Returns the pubkey associated with a particular alias
    
    Parameters:
        alias (int): The alias to get the public key for
    """
    con = sqlite3.connect("aliases.db")
    with con:
        cur = con.cursor()
        return cur.execute(
            "SELECT pubkey FROM aliases WHERE alias = ?", (alias,)
        ).fetchone()[0]


def get_claimed_aliases():
    """
    Gets all of the alias, pubkey pairs from the database
    
    Returns: dictionary of {alias : pubkey}
    """
    con = sqlite3.connect("aliases.db")
    pairs = {}
    with con:
        cur = con.cursor()
        for row in cur.execute("SELECT * FROM aliases WHERE pubkey IS NOT NULL"):
            pairs[row[0]]=row[1]
    return pairs