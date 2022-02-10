"""
Definitions specific to ART



"""
# Parameters to be modfied for each snapshot

#nstars = 50000
#path=  "/Users/sroca/Postdoc/Simulations/MW_003/RUN2.1/"
#filename= "PMcrs0a1.000.DAT"
#path= '/Users/sroca/Postdoc/UNAM/Aillsim/N106/RUNbar/'
#filename= "PMcrs0a0.6490.DAT"
#nstars = 999978

# CIs
#path= '/Users/sroca/Desktop/Ciencia/RODIN/CIbar/N106/'
#filename= "PMcrs0.DAT"
#nstars = 999978


###### YOU MUST NOT CHANGE THE FOLLOWING FIELDS #######

# If not otherwise specified, we are big endian
endian = '>'

particle_fields = [
    'particle_mass',  # stars have variable mass
    'particle_index',
    'particle_type',
    'particle_position_x',
    'particle_position_y',
    'particle_position_z',
    'particle_velocity_x',
    'particle_velocity_y',
    'particle_velocity_z',
    'particle_mass_initial',
]

filename_pattern = {
    'particle_header': ['PMcrd', '.DAT'],
    'particle_data': ['PMcrs0', '.DAT'],
    'particle_stars': ['stars', '.dat']
}

dmparticle_header_struct = [
     ('header',
     'aexpn', 'aexp0', 'amplt', 'astep',
     'istep',
     'partw', 'tintg',
     'Ekin', 'Ekin1', 'Ekin2',
     'au0', 'aeu0',
     'Nrow', 'Ngridc', 'Nspecies', 'Nseed',
     'Om0', 'Oml0', 'hubble', 'Wp5', 'Ocurv',
     'wspecies','lspecies',
     'extras1','Rs','Md','extras2', 'boxsize'),
     (1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
     1,1,1,10,10,71,1,1,6,1)
]

constants = {
    "Y_p": 0.245,
    "gamma": 5./3.,
    "T_CMB0": 2.726,
    "T_min": 300.,
    "wmu": 4.0/(8.0-5.0*0.245),
}

seek_extras = 137
