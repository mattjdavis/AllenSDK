import numpy as np
import logging

from allensdk.model.glif.find_spikes import find_spikes, find_spikes_list

from allensdk.ephys.extract_cell_features import get_stim_characteristics

def smooth(voltage, current, filter_size_s, dt):
    '''Smooths voltage, current, and dV/dt for use in least squares R, C, El calculation.
    Note that currently there is still a bit of question about the order of the convolution
    operation and how similar it should be if the smoothed dv/dt is calculated by first 
    smoothing the voltage and then calculating dV/dt or by calculating dV/dt first and then 
    smoothing.  In practice these numbers are very similar (within e-12) however that 
    difference is still intriguing.  Please see experimental smooth function in 
    verify_rcel_GLM.py (in the GLIF_clean verification folder)
    
    inputs:
        voltage: numpy array of voltage time series
        current: numpy array of current time series
        filter_size_s: float of the size of the filter in seconds
        dt: float size of time step in time series
    outputs:
        sm_v: numpy array of voltage time series smoothed with the filter
        sm_i: numpy array of current time series smoothed with the filter
        sm_dvdt: numpy array of v time series smoothed with the filter
    '''
    #Square filter for smoothing
    sq_filt = np.ones((round(filter_size_s/dt,1)))
    sq_filt = sq_filt/len(sq_filt)
    
    #take diff and then smooth
    i = current[0:len(voltage)-1]
    v = voltage[0:len(voltage)-1]
    vs = voltage[1:len(voltage)]   
    
    #smooth data and diff
    sm_v = np.convolve(v,sq_filt,'same')
    sm_vs = np.convolve(vs,sq_filt,'same')
    sm_i = np.convolve(i,sq_filt,'same')
    sm_dvdt = (sm_vs-sm_v)/dt

    return sm_v, sm_i, sm_dvdt


def least_squares_simple_circuit_with_smoothing_fit_RCEl(voltage_list, current_list, dt, filter_size, no_rest=False):
    '''Calculate resistance, capacitance and resting potential by performing 
    least squares on a smoothed current and voltage.
    inputs:
        voltage_list: list of voltage responses for several sweep repeats
        current_list: list of current injections for several sweep repeats
        dt: time step size
    outputs:
        list of capacitance, resistance and resting potential values for each sweep
    '''
    r_list=[]
    c_list=[]
    El_list=[]
    for voltage, current in zip(voltage_list, current_list):
        sm_v, sm_i, sm_dvdt=smooth(voltage, current, filter_size, dt)
        matrix_sm=np.ones((len(sm_v), 3))
        matrix_sm[:,0]=sm_v
        matrix_sm[:,1]=sm_i
        
        lsq_der_sm=np.linalg.lstsq(matrix_sm, sm_dvdt)[0] 
        C=1/lsq_der_sm[1]
        R=-1/(C*lsq_der_sm[0])
        El=C*R*lsq_der_sm[2]
        
        r_list.append(R)
        c_list.append(C)
        El_list.append(El)
    return R, C, El

def least_squares_simple_circuit_fit_RCEl(voltage_list, current_list, dt, no_rest=False):
    '''Calculate resistance, capacitance and resting potential by performing 
    least squares on current and voltage.
    inputs:
        voltage_list: list of voltage responses for several sweep repeats
        current_list: list of current injections for several sweep repeats
        dt: time step size
    outputs:
        list of capacitance, resistance and resting potential values for each sweep
    '''
    capacitance_list=[]
    resistance_list=[]
    El_list=[]
    for voltage, current in zip(voltage_list, current_list): 
        spikes, _ = find_spikes_list([voltage], dt)
        if len(spikes[0]) > 0:
            logging.warning('There is a spike in your subthreshold noise. However continuing using least squares')
        if no_rest:
            #find region of stimulus. Note this will only work if there is no test pulse and only one stimulus injection (i.e. entire noise sweep is already truncated to just low amplitude noise injection)
            t = np.arange(0, len(current)) * dt
            (_, _, _, start_idx, end_idx) = get_stim_characteristics(current, t, no_test_pulse=True)
            stim_dur = end_idx - start_idx
            stim_start = start_idx

            voltage = voltage[stim_start:stim_start+stim_dur]
            current = current[stim_start:stim_start+stim_dur]   

        v_nplus1=voltage[1:]
        voltage=voltage[0:-1]
        current=current[0:-1]
        matrix=np.ones((len(voltage), 3))
        matrix[:,0]=voltage
        matrix[:,1]=current
        out=np.linalg.lstsq(matrix, v_nplus1)[0] 
        
        capacitance=dt/out[1]
        resistance=dt/(capacitance*(1-out[0]))
        El=(capacitance*resistance*out[2])/dt
           
        capacitance_list.append(capacitance)
        resistance_list.append(resistance)
        El_list.append(El)    
        
#    print "R via least squares", np.mean(resistance_list)*1e-6, "Mohms"
#    print "C via least squares", np.mean(capacitance_list)*1e12, "pF"
#    print "El via least squares", np.mean(El_list)*1e3, "mV" 
#    print "tau", np.mean(resistance_list)*np.mean(capacitance_list)*1e3, "ms"
    
    return resistance_list, capacitance_list, El_list


def least_squares_simple_circuit_fit_REl(voltage_list, current_list, Cap, dt):
    '''Calculate resistance and resting potential by performing 
    least squares on current and voltage.
    inputs:
        voltage_list: list of voltage responses for several sweep repeats
        current_list: list of current injections for several sweep repeats
        Cap: capacitance (float) 
        dt: time step size
    outputs:
        list of resistance and resting potential values for each sweep
    '''
    resistance_list=[]
    El_list=[]
    for voltage, current in zip(voltage_list, current_list):    
        v_nplus1=voltage[1:]
        voltage=voltage[0:-1]
        current=current[0:-1]
        matrix=np.ones((len(voltage), 2))
        matrix[:,0]=voltage
        out=np.linalg.lstsq(matrix, v_nplus1-(current*dt)/Cap)[0] 
        
        resistance=dt/(Cap*(1-out[0]))
        El=(Cap*resistance*out[1])/dt        
        
        resistance_list.append(resistance)
        El_list.append(El)    
    
#    print "R via least squares", np.mean(resistance_list)*1e-6, "Mohms"
#    print "C via least squares", np.mean(capacitance_list)*1e12, "pF"
#    print "El via least squares", np.mean(El_list)*1e3, "mV" 
#    print "tau", np.mean(resistance_list)*np.mean(capacitance_list)*1e3, "ms"
    
    return resistance_list, El_list
