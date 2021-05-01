# -*- coding: utf-8 -*-
"""
Created on Sat Oct 31 09:03:05 2020

@author: mthripp1
"""

import numpy as np
from scipy.optimize import root, minimize

from dce import relax

# TODO
# jupyter notebooks for pk_models etc.
# ADD more MODELS
# ADD T1 FITTING
# DOCUMENTATION
# DEAL WITH FIT WARNINGS
# optimise tolerances etc.
# EXCEPTIONS
# ADD MULTISTART

def s_to_e(s, base_idx):
    s_pre = np.mean(s[base_idx])
    e = 100.*((s - s_pre)/s_pre)
    return e

def e_to_c(e, k, r0, c_to_r_model, signal_model):
    # convert enh to conc for one time point
    def e_to_c_single(enh):
        res = root(lambda c: enh - c_to_e(c, k, r0, c_to_r_model, signal_model),
                x0= 0., method='hybr', options={'maxfev': 1000, 'xtol': 1e-7})
        assert res.success, 'Enh-to-conc root finding failed.'
        return min(res.x)
    # apply to all time points
    c = np.asarray( [e_to_c_single(enh) for enh in e] )
    return c

def c_to_e(c, k, r0, c_to_r_model, signal_model):
    #convert concentration to enhancement assuming fxl
    r = c_to_r_model.r_single(r0, c)
    s_pre = signal_model.signal(1., r0, k)
    s_post = signal_model.signal(1., r, k)
    e = 100. * ((s_post - s_pre) / s_pre)
    return e

def c_to_pkp(C_t, pk_model, fit_opts = None):
    if 't_mask' not in fit_opts:
        fit_opts['t_mask'] = np.ones(C_t.shape)
        
    # list of variable parameters = s0 + variable PK parameters
    x_0 = pk_model.pkp_array(fit_opts['pk_pars_0'])
    x_scalefactor = pk_model.typical_pars
    x_0_norm = x_0 / x_scalefactor    
    
    #define function to minimise
    def cost(x_norm, *args):
        x = x_norm * x_scalefactor
        C_t_try, _C_cp, _C_e = pk_model.conc(*x)
        ssq = np.sum(fit_opts['t_mask']*((C_t_try - C_t)**2))    
        return ssq
    
    #perform fitting
    result = minimize(cost, x_0_norm, args=None,
             method='trust-constr', bounds=None, constraints=pk_model.constraints)#method='trust-constr', bounds=bounds, constraints=models.pkp_constraints[irf_model])

    x_opt = result.x * x_scalefactor
    pk_pars_opt = pk_model.pkp_dict(x_opt)
    C_fit, _C_cp, _C_e = pk_model.conc(*x_opt)
    C_fit[np.logical_not(fit_opts['t_mask'])]=np.nan
    
    return pk_pars_opt, C_fit


def s_to_pkp(s, hct, k, r0_tissue, r0_blood, pk_model, c_to_r_model, water_ex_model, signal_model, fit_opts=None):

    if 't_mask' not in fit_opts:
        fit_opts['t_mask'] = np.ones(s.shape)

    # estimate s0, scale parameters
    s0_0 = s[0] / signal_model.signal(1., r0_tissue)
    
    # list of variable parameters = s0 + variable PK parameters
    x_0 = np.array( [ s0_0, *pk_model.pkp_array(fit_opts['pk_pars_0']) ] )

    x_scalefactor = np.array( [ s0_0, *pk_model.typical_pars ] )
    
    x_0_norm = x_0 / x_scalefactor    
    #TODO: implement bounds and constraints
    #x_lb_norm = pkp_to_x(proc.fit_opts['pk_pars_lb'], s0_0*0.5, proc.irf_model) / x_sf
    #x_ub_norm = pkp_to_x(proc.fit_opts['pk_pars_ub'], s0_0*1.5, proc.irf_model) / x_sf
    #bounds = list(zip(x_lb_norm, x_ub_norm))   
    
    #define function to minimise
    def cost(x_norm, *args):
        x = x_norm * x_scalefactor
        s0_try = x[0]
        pk_pars_try = pk_model.pkp_dict(x[1:])
        s_try = pkp_to_s(pk_pars_try, hct, s0_try, k, r0_tissue, r0_blood, pk_model, c_to_r_model, water_ex_model, signal_model)
        ssq = np.sum(fit_opts['t_mask']*((s_try - s)**2))    
        return ssq
    
    #perform fitting
    result = minimize(cost, x_0_norm, args=None,
             method='trust-constr', bounds=None, constraints=pk_model.constraints)#method='trust-constr', bounds=bounds, constraints=models.pkp_constraints[irf_model])

    x_opt = result.x * x_scalefactor
    s0_opt = x_opt[0]
    pk_pars_opt = pk_model.pkp_dict(x_opt[1:])

    s_fit = pkp_to_s(pk_pars_opt, hct, s0_opt, k, r0_tissue, r0_blood, pk_model, c_to_r_model, water_ex_model, signal_model)
    s_fit[np.logical_not(fit_opts['t_mask'])]=np.nan
    
    return pk_pars_opt, s0_opt, s_fit




def pkp_to_s(pk_pars, hct, s0, k, r0_tissue, r0_blood, pk_model, c_to_r_model, water_ex_model, signal_model):   
   
    C_t, C_cp, C_e = pk_model.conc(**pk_pars)     
    v_compa = pkp_to_v(pk_pars, hct)    
    c_compa = { 'b': C_cp / v_compa['b'],
                'e': C_e / v_compa['e'],
                'i': np.zeros(C_e.shape) }
    p_compa = v_compa
       
    r0_extravasc = relax.relaxation(
        r_1 = (r0_tissue.r_1-p_compa['b']*r0_blood.r_1)/(1-p_compa['b']),
        r_2s = r0_tissue.r_2s )
    
    r0_compa = { 'b': r0_blood,
                 'e': r0_extravasc,
                 'i': r0_extravasc }
   
    r_compa = c_to_r_model.r_compa(r0_compa, c_compa)        
    s = water_ex_model.r_compa_to_s(s0, p_compa, r_compa, signal_model, k)
    
    return s

def pkp_to_v(pk_pars, hct):
    # if vp exists, calculate vb, otherwise set vb to zero
    if 'vp' in pk_pars:
        vb = pk_pars['vp'] / (1 - hct)
    else:
        vb = 0
    
    # if ve exists define vi as remaining volume, otherwise set to vi zero
    if 've' in pk_pars:
        ve = pk_pars['ve']
        vi = 1 - vb - ve
    else:
        ve = 1 - vb
        vi = 0    
    
    v = {'b': vb, 'e': ve, 'i': vi}
    return v
    
    