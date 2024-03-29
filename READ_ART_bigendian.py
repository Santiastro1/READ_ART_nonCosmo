import glob
import numpy as np
import os
import stat
import struct
import weakref
from functools import lru_cache
from matplotlib import pyplot as plt

from definitions import \
    particle_fields, \
    filename_pattern, \
    dmparticle_header_struct, \
    constants, \
    seek_extras
#    nstars, \
#    path, \
#    filename

class ART_INPUT:
 def __init__(self, path, filename, nstars, dataset_type='art',
                 fields=None, storage_filename=None,
                 skip_particles=False, skip_stars=False,
                 limit_level=None, spread_age=True,
                 force_max_level=None, file_particle_header=None,
                 file_particle_data=None, file_particle_stars=None,
                 units_override=None):
        self._fields_in_file = fields
        self.cache = {}
        self._file_art = filename
        self._file_path = path
        self._file_particle_header = file_particle_header
        self._file_particle_data = file_particle_data
        self._file_particle_stars = file_particle_stars
        self._find_files(filename,path)
        self.parameter_filename = filename
        self.skip_particles = skip_particles
        self.skip_stars = skip_stars
        self.limit_level = limit_level
        self.max_level = limit_level
        self.force_max_level = force_max_level
        self.spread_age = spread_age
        self.storage_filename = storage_filename

 def _find_files(self,filename,path):
        """
        Given the AMR base filename, attempt to find the
        particle header, star files, etc.
        """
        base_prefix, base_suffix = filename_pattern['particle_data']
        numericstr = filename.rsplit('rs0',1)[1].replace(base_suffix,'')
        possibles = glob.glob(path+"*")
        for filetype, (prefix, suffix) in filename_pattern.items():
            # if this attribute is already set skip it
            if getattr(self, "_file_"+filetype, None) is not None:
                continue
            match = None
            for possible in possibles:
                prefix1=path+prefix
                if possible.endswith(numericstr+suffix):
                    if possible.startswith(prefix1):
                        match = possible
                elif possible.endswith(suffix):
                  if match is None:
                    if possible.startswith(prefix1):
                        match = possible
            if match is not None:
                print('discovered %s:%s', filetype, match)
                setattr(self, "_file_"+filetype, match)
            else:
                setattr(self, "_file_"+filetype, None)

 def _parse_parameter_file(self,nstars):
        """
        Get the various simulation parameters & constants.
        """
        self.domain_left_edge = np.zeros(3, dtype='float')
        self.domain_right_edge = np.zeros(3, dtype='float')+1.0
        self.dimensionality = 3
        self.refine_by = 2
        self.periodicity = (True, True, True)
        self.cosmological_simulation = True
        self.parameters = {}
        self.parameters.update(constants)
        self.parameters['Time'] = 1.0
        self.file_count = 1
        self.filename_template = self.parameter_filename

        # read the particle header
        self.particle_types = []
        self.particle_types_raw = ()
        assert self._file_particle_header
        with open(self._file_particle_header, "rb") as fh:
            seek = 4
            fh.seek(seek)
            headerstr = np.fromfile(fh, count=1, dtype='>S45')
            aexpn = np.fromfile(fh, count=1, dtype='>f4')
            aexp0 = np.fromfile(fh, count=1, dtype='>f4')
            amplt = np.fromfile(fh, count=1, dtype='>f4')
            astep = np.fromfile(fh, count=1, dtype='>f4')
            istep = np.fromfile(fh, count=1, dtype='>i4')
            partw = np.fromfile(fh, count=1, dtype='>f4')
            tintg = np.fromfile(fh, count=1, dtype='>f4')
            ekin = np.fromfile(fh, count=1, dtype='>f4')
            ekin1 = np.fromfile(fh, count=1, dtype='>f4')
            ekin2 = np.fromfile(fh, count=1, dtype='>f4')
            au0 = np.fromfile(fh, count=1, dtype='>f4')
            aeu0 = np.fromfile(fh, count=1, dtype='>f4')
            nrowc = np.fromfile(fh, count=1, dtype='>i4')
            ngridc = np.fromfile(fh, count=1, dtype='>i4')
            nspecs = np.fromfile(fh, count=1, dtype='>i4')
            nseed = np.fromfile(fh, count=1, dtype='>i4')
            Om0 = np.fromfile(fh, count=1, dtype='>f4')
            Oml0 = np.fromfile(fh, count=1, dtype='>f4')
            hubble = np.fromfile(fh, count=1, dtype='>f4')
            Wp5 = np.fromfile(fh, count=1, dtype='>f4')
            Ocurv = np.fromfile(fh, count=1, dtype='>f4')
            wspecies = np.fromfile(fh, count=10, dtype='>f4')
            lspecies = np.fromfile(fh, count=10, dtype='>i4')
            extras1 = np.fromfile(fh, count=71, dtype='>f4')
            Rs = np.fromfile(fh, count=1, dtype='>f4')
            Md = np.fromfile(fh, count=1, dtype='>f4')
            Mh = np.fromfile(fh, count=1, dtype='>f4')
            Rd = np.fromfile(fh, count=1, dtype='>f4')
            Consentr = np.fromfile(fh, count=1, dtype='>f4')
            extras2 = np.fromfile(fh, count=3, dtype='>f4')
            boxsize = np.fromfile(fh, count=1, dtype='>f4')
        n = int(nspecs)
        particle_header_vals = {}
        tmp = np.array([headerstr, aexpn, aexp0, amplt, astep, istep,
            partw, tintg, ekin, ekin1, ekin2, au0, aeu0, nrowc, ngridc,
            nspecs, nseed, Om0, Oml0, hubble, Wp5, Ocurv, wspecies,
            lspecies, extras1,Rs,Md,extras2, boxsize],dtype=object)
        print(tmp)
        for i in range(len(tmp)):
            a1 = dmparticle_header_struct[0][i]
            a2 = dmparticle_header_struct[1][i]
            if a2 == 1:
                particle_header_vals[a1] = tmp[i][0]
            else:
                particle_header_vals[a1] = tmp[i][:a2]
        for specie in range(n):
            self.particle_types.append("specie%i" % specie)
        self.particle_types_raw = tuple(
            self.particle_types)
        ls_nonzero = np.diff(lspecies)[:n-1]
        ls_nonzero = np.append(lspecies[0], ls_nonzero)
        self.star_type = len(ls_nonzero)
        for k, v in particle_header_vals.items():
            if k in self.parameters.keys():
                if not self.parameters[k] == v:
                    print(
                        "Inconsistent parameter %s %1.1e  %1.1e", k, v,
                        self.parameters[k])
            else:
                self.parameters[k] = v
        self.parameters_particles = particle_header_vals
        self.parameters.update(particle_header_vals)
        self.parameters['wspecies'] = wspecies[:n]
        self.parameters['lspecies'] = lspecies[:n]
        self.parameters['ng'] = self.parameters['Ngridc']
        self.parameters['ncell0'] = self.parameters['ng']**3
        self.parameters['boxh'] = self.parameters['boxsize']
        self.parameters['total_particles'] = ls_nonzero
        self.parameters["Nrow"]=nrowc
        self.parameters["Rs"]=Rs
        self.parameters["Mdisk"]=Md
        self.parameters["Mhalo"]=Mh
        self.parameters["CNFW"]=Consentr
        self.domain_dimensions = np.ones(3,
                        dtype='int64')*2 # NOT ng

        # setup standard simulation params yt expects to see
        self.current_redshift = self.parameters["aexpn"]**-1.0 - 1.0
        self.omega_lambda = particle_header_vals['Oml0']
        self.omega_matter = particle_header_vals['Om0']
        self.hubble_constant = particle_header_vals['hubble']
#        self.scaleV=1./(self.parameters['boxsize']*100/2.08e-3/np.sqrt(self.parameters["Mhalo"]/self.parameters["Rs"]/(np.log(1.+self.parameters["CNFW"])-self.parameters["CNFW"]/(1.+self.parameters["CNFW"])))/self.parameters["aexpn"]/self.parameters['ng'])
        self.scaleV=self.parameters['boxsize']*100/particle_header_vals["aexpn"]/self.parameters['ng']
        self.scaleM=Md/nstars/particle_header_vals['hubble']#(self.parameters['boxsize']**3/**3*particle_header_vals['Om0']/particle_header_vals['hubble']/(3.64e-12))
        self.parameters['Mass_sp']=wspecies[:n]*(self.parameters['boxsize']**3/self.parameters['ng']**3*particle_header_vals['Om0']/particle_header_vals['hubble']/(3.64e-12))
        self.scaleC=particle_header_vals["aexpn"]/particle_header_vals['hubble']*1000.*self.parameters['boxsize'] # 1/ng already applied when reading the particle_position data ( if fname.startswith("particle_position_%s" % ax):# This is not the same as domain_dimensions)
        self.min_level = 0
        self.max_level = 0
#        self.min_level = particle_header_vals['min_level']
#        self.max_level = particle_header_vals['max_level']
#        if self.limit_level is not None:
#            self.max_level = min(
#                self.limit_level, particle_header_vals['max_level'])
#        if self.force_max_level is not None:
#            self.max_level = self.force_max_level
        self.hubble_time = 1.0/(self.hubble_constant*100/3.08568025e19)
        self.gamma = self.parameters["gamma"]
        self.ws = self.parameters["wspecies"]
        self.ls = self.parameters["lspecies"]
        self.file_particle = self._file_particle_data
        self.Nrow = self.parameters["Nrow"]
        self.Ngrid = self.parameters["ng"]
 def _get_field(self,  field):
        tr = {}
        ftype, fname = field
        ptmax = self.ws[-1]
        pbool, idxa, idxb = _determine_field_size(self, ftype,
                                                  self.ls, ptmax)
        npa = idxb - idxa
        sizes = np.diff(np.concatenate(([0], self.ls)))
        rp = lambda ax: read_particles(
            self._file_particle_data, self.Nrow[0], idxa=idxa,
            idxb=idxb, fields=ax)
        for i, ax in enumerate('xyz'):
            if fname.startswith("particle_position_%s" % ax):
                # This is not the same as domain_dimensions
                dd = self.parameters['ng']
                off = 1.0/dd
                tr[field] = rp([ax])[0]/dd - off
            if fname.startswith("particle_velocity_%s" % ax):
                tr[field], = rp(['v'+ax])
        if fname.startswith("particle_mass"):
            a = 0
            data = np.zeros(npa, dtype='f8')
            for ptb, size, m in zip(pbool, sizes, self.ws):
                if ptb:
                    data[a:a+size] = m
                    a += size
            tr[field] = data
        elif fname == "particle_index":
            tr[field] = np.arange(idxa, idxb)
        elif fname == "particle_type":
            a = 0
            data = np.zeros(npa, dtype='int')
            for i, (ptb, size) in enumerate(zip(pbool, sizes)):
                if ptb:
                    data[a: a + size] = i
                    a += size
            tr[field] = data
        # We check again, after it's been filled
        if fname.startswith("particle_mass"):
            # We now divide by NGrid in order to make this match up.  Note that
            # this means that even when requested in *code units*, we are
            # giving them as modified by the ng value.  This only works for
            # dark_matter -- stars are regular matter.
            tr[field] /= self.domain_dimensions.prod()
        if tr == {}:
            tr[field] = np.array([])
        self.cache[field] = tr[field]
        return self.cache[field]

 def _read_particle_fields(self):
        field_list = particle_fields
        # What we need is a mapping from particle types to return types
        for ptype in self.particle_types_raw:
            x = self._get_field((ptype, "particle_position_x"))
            y = self._get_field((ptype, "particle_position_y"))
            z = self._get_field((ptype, "particle_position_z"))
            for field in field_list:
                    data = self._get_field((ptype, field))
                    yield (ptype, field), data[None]
def read_particles(file, Nrow, idxa, idxb, fields):
    words = 6  # words (reals) per particle: x,y,z,vx,vy,vz
    real_size = 4  # for file_particle_data; not always true?
    np_per_page = Nrow**2  # defined in ART a_setup.h, # of particles/page
    num_pages = os.path.getsize(file)/(real_size*words*np_per_page)
    fh = open(file, 'r')
    skip, count = idxa, idxb - idxa
    kwargs = dict(words=words, real_size=real_size,
                  np_per_page=np_per_page, num_pages=num_pages)
    arrs = []
    for field in fields:
        ranges = get_ranges(skip, count, field, **kwargs)
        data = None
        for seek, this_count in ranges:
            fh.seek(seek)
            temp = np.fromfile(fh, count=this_count, dtype='>f4')
            if data is None:
                data = temp
            else:
                data = np.concatenate((data, temp))
        arrs.append(data.astype('f8'))
    fh.close()
    return arrs

def _determine_field_size(pf,field,lspecies, ptmax):
    pbool = np.zeros(len(lspecies), dtype="bool")
    idxas = np.concatenate(([0, ], lspecies[:-1]))
    idxbs = lspecies
    if "specie" in field:
        index = int(field.replace("specie", ""))
        pbool[index] = True
    else:
        raise RuntimeError
    idxa, idxb = idxas[pbool][0], idxbs[pbool][-1]
    return pbool, idxa, idxb


def find_root(f, a, b, tol=1e-6):
    c = (a+b)/2.0
    last = -np.inf
    assert(np.sign(f(a)) != np.sign(f(b)))
    while np.abs(f(c)-last) > tol:
        last = f(c)
        if np.sign(last) == np.sign(f(b)):
            b = c
        else:
            a = c
        c = (a+b)/2.0
    return c

def quad(fintegrand, xmin, xmax, n=1e4):
    spacings = np.logspace(np.log10(xmin), np.log10(xmax), n)
    integrand_arr = fintegrand(spacings)
    val = np.trapz(integrand_arr, dx=np.diff(spacings))
    return val

def get_ranges(skip, count, field, words, real_size, np_per_page,
                  num_pages):
    #translate every particle index into a file position ranges
    ranges = []
    arr_size = np_per_page * real_size
    idxa, idxb = 0, 0
    posa, posb = 0, 0
    for page in np.arange(num_pages):
        idxb += np_per_page
        for i, fname in enumerate(['x', 'y', 'z', 'vx', 'vy', 'vz']):
            posb += arr_size
            if i == field or fname == field:
                if skip < np_per_page and count > 0:
                    left_in_page = np_per_page - skip
                    this_count = min(left_in_page, count)
                    count -= this_count
                    start = posa + skip * real_size
                    end = posa + this_count * real_size
                    ranges.append((start, this_count))
                    skip = 0
                    assert end <= posb
                else:
                    skip -= np_per_page
            posa += arr_size
        idxa += np_per_page
    assert count == 0
    return ranges



def read_ART(path,filename,nstars):
    stars=[]
    ART_IO = ART_INPUT(path,filename,nstars)
    ART_IO._parse_parameter_file(nstars)
    data=ART_IO._read_particle_fields()
    nspec=len(ART_IO.parameters['wspecies'])
    ng=ART_IO.parameters['ng']
    dm0=[]
    dm1=[]
    dm2=[]
    dm3=[]
    dm4=[]
    dm5=[]
    dm6=[]
    dm7=[]
    dm8=[]
    dm9=[]
    for i in data:
     if i[0][0] == 'specie0':
      stars.append(i[1][0,:nstars])
      dm0.append(i[1][0,nstars+1:])
     if nspec>1:
      if i[0][0] == 'specie1':
       dm1.append(i[1][0,:])
     if nspec>2:
       if i[0][0] == 'specie2':
        dm2.append(i[1][0,:])
     if nspec>3:
      if i[0][0] == 'specie3':
       dm3.append(i[1][0,:])
     if nspec>4:
      if i[0][0] == 'specie4':
       dm4.append(i[1][0,:])
     if nspec>5:
      if i[0][0] == 'specie5':
       dm5.append(i[1][0,:])
     if nspec>6:
      if i[0][0] == 'specie6':
       dm6.append(i[1][0,:])
     if nspec>7:
      if i[0][0] == 'specie7':
       dm7.append(i[1][0,:])
     if nspec>8:
      if i[0][0] == 'specie8':
       dm8.append(i[1][0,:])
     if nspec>9:
      if i[0][0] == 'specie9':
       dm9.append(i[1][0,:])
     if nspec>10:
       print('TOO MANY PARTICLE SPECIES!!!')
    print('After appending')
    mass=[]
    x=[]
    y=[]
    z=[]
    x_test=[]
    y_test=[]
    z_test=[]
    vx=[]
    vy= []
    vz=[]
    Id=[]
    mass.append(stars[0][:]*0.+ART_IO.parameters['Mass_sp'][0])
    mass.append(dm0[0][:]*0.+ART_IO.parameters['Mass_sp'][0])
    Id.append(stars[1][:])
    Id.append(dm0[1][:])
    x_test.append((stars[3][:]))
    xmean=np.mean(x_test)
    y_test.append((stars[4][:]))
    ymean=np.mean(y_test)
    z_test.append((stars[5][:]))
    zmean=np.mean(z_test)
    x.append((stars[3][:]-xmean)*ART_IO.scaleC)
    y.append((stars[4][:]-ymean)*ART_IO.scaleC)
    z.append((stars[5][:]-zmean)*ART_IO.scaleC)
    vx.append((stars[6][:])*ART_IO.scaleV)
    vy.append((stars[7][:])*ART_IO.scaleV)
    vz.append((stars[8][:])*ART_IO.scaleV)
    x.append((dm0[3][:]-xmean)*ART_IO.scaleC)
    y.append((dm0[4][:]-ymean)*ART_IO.scaleC)
    z.append((dm0[5][:]-zmean)*ART_IO.scaleC)
    vx.append((dm0[6][:])*ART_IO.scaleV)
    vy.append((dm0[7][:])*ART_IO.scaleV)
    vz.append((dm0[8][:])*ART_IO.scaleV)
    if nspec>1:
     mass.append(dm1[0][:]*0.+ART_IO.parameters['Mass_sp'][1])
     x.append((dm1[3][:]-xmean)*ART_IO.scaleC)
     y.append((dm1[4][:]-ymean)*ART_IO.scaleC)
     z.append((dm1[5][:]-zmean)*ART_IO.scaleC)
     vx.append((dm1[6][:])*ART_IO.scaleV)
     vy.append((dm1[7][:])*ART_IO.scaleV)
     vz.append((dm1[8][:])*ART_IO.scaleV)
     Id.append(dm1[1][:])
    if nspec>2:
     mass.append(dm2[0][:]*0.+ART_IO.parameters['Mass_sp'][2])
     x.append((dm2[3][:]-xmean)*ART_IO.scaleC)
     y.append((dm2[4][:]-ymean)*ART_IO.scaleC)
     z.append((dm2[5][:]-zmean)*ART_IO.scaleC)
     vx.append((dm2[6][:])*ART_IO.scaleV)
     vy.append((dm2[7][:])*ART_IO.scaleV)
     vz.append((dm2[8][:])*ART_IO.scaleV)
     Id.append(dm2[1][:])
    if nspec>3:
     mass.append(dm3[0][:]*0.+ART_IO.parameters['Mass_sp'][3])
     x.append((dm3[3][:]-xmean)*ART_IO.scaleC)
     y.append((dm3[4][:]-ymean)*ART_IO.scaleC)
     z.append((dm3[5][:]-zmean)*ART_IO.scaleC)
     vx.append((dm3[6][:])*ART_IO.scaleV)
     vy.append((dm3[7][:])*ART_IO.scaleV)
     vz.append((dm3[8][:])*ART_IO.scaleV)
     Id.append(dm3[1][:])
    if nspec>4:
     mass.append(dm4[0][:]*0.+ART_IO.parameters['Mass_sp'][4])
     x.append((dm4[3][:]-xmean)*ART_IO.scaleC)
     y.append((dm4[4][:]-ymean)*ART_IO.scaleC)
     z.append((dm4[5][:]-zmean)*ART_IO.scaleC)
     vx.append((dm4[6][:])*ART_IO.scaleV)
     vy.append((dm4[7][:])*ART_IO.scaleV)
     vz.append((dm4[8][:])*ART_IO.scaleV)
     Id.append(dm4[1][:])
    if nspec>5:
     mass.append(dm5[0][:]*0.+ART_IO.parameters['Mass_sp'][5])
     x.append((dm5[3][:]-xmean)*ART_IO.scaleC)
     y.append((dm5[4][:]-ymean)*ART_IO.scaleC)
     z.append((dm5[5][:]-zmean)*ART_IO.scaleC)
     vx.append((dm5[6][:])*ART_IO.scaleV)
     vy.append((dm5[7][:])*ART_IO.scaleV)
     vz.append((dm5[8][:])*ART_IO.scaleV)
     Id.append(dm5[1][:])
    if nspec>6:
     mass.append(dm6[0][:]*0.+ART_IO.parameters['Mass_sp'][6])
     x.append((dm6[3][:]-xmean)*ART_IO.scaleC)
     y.append((dm6[4][:]-ymean)*ART_IO.scaleC)
     z.append((dm6[5][:]-zmean)*ART_IO.scaleC)
     vx.append((dm6[6][:])*ART_IO.scaleV)
     vy.append((dm6[7][:])*ART_IO.scaleV)
     vz.append((dm6[8][:])*ART_IO.scaleV)
     Id.append(dm6[1][:])
    if nspec>7:
     mass.append(dm7[0][:]*0.+ART_IO.parameters['Mass_sp'][7])
     x.append((dm7[3][:]-xmean)*ART_IO.scaleC)
     y.append((dm7[4][:]-ymean)*ART_IO.scaleC)
     z.append((dm7[5][:]-zmean)*ART_IO.scaleC)
     vx.append((dm7[6][:])*ART_IO.scaleV)
     vy.append((dm7[7][:])*ART_IO.scaleV)
     vz.append((dm7[8][:])*ART_IO.scaleV)
     Id.append(dm7[1][:])
    if nspec>8:
     mass.append(dm8[0][:]*0.+ART_IO.parameters['Mass_sp'][8])
     x.append((dm8[3][:]-xmean)*ART_IO.scaleC)
     y.append((dm8[4][:]-ymean)*ART_IO.scaleC)
     z.append((dm8[5][:]-zmean)*ART_IO.scaleC)
     vx.append((dm8[6][:])*ART_IO.scaleV)
     vy.append((dm8[7][:])*ART_IO.scaleV)
     vz.append((dm8[8][:])*ART_IO.scaleV)
     Id.append(dm8[1][:])
    if nspec>9:
     mass.append(dm9[0][:]*0.+ART_IO.parameters['Mass_sp'][9])
     x.append((dm9[3][:]-xmean)*ART_IO.scaleC)
     y.append((dm9[4][:]-ymean)*ART_IO.scaleC)
     z.append((dm9[5][:]-zmean)*ART_IO.scaleC)
     vx.append((dm9[6][:])*ART_IO.scaleV)
     vy.append((dm9[7][:])*ART_IO.scaleV)
     vz.append((dm9[8][:])*ART_IO.scaleV)
     Id.append(dm9[1][:])
    return mass,x,y,z,vx,vy,vz,Id
