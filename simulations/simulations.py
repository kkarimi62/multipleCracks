def makeOAR( EXEC_DIR, node, core, time ):
	someFile = open( 'oarScript.sh', 'w' )
	print >> someFile, '#!/bin/bash\n'
	print >> someFile, 'EXEC_DIR=%s\n' %( EXEC_DIR )
	print >> someFile, 'MEAM_library_DIR=%s\n' %( MEAM_library_DIR )
#	print >> someFile, 'source ~/Project/opt/deepmd-kit/bin/activate ~/Project/opt/deepmd-kit\nexport OMP_NUM_THREADS=%s'%(nThreads*nNode) #--- deep potential stuff
	print >> someFile, 'module load openmpi/4.0.2-gnu730\nmodule load lib/openblas/0.3.13-gnu\n'

	#--- run python script 
#	 print >> someFile, "$EXEC_DIR/%s < in.txt -var OUT_PATH %s -var MEAM_library_DIR %s"%( EXEC, OUT_PATH, MEAM_library_DIR )
#	cutoff = 1.0 / rho ** (1.0/3.0)
	for script,var,indx, execc in zip(Pipeline,Variables,range(100),EXEC):
		if execc == 'lmp': #_mpi' or EXEC == 'lmp_serial':
			print >> someFile, "mpirun --oversubscribe -np %s $EXEC_DIR/%s < %s -echo screen -var OUT_PATH \'%s\' -var PathEam %s -var INC \'%s\' %s\n"%(nThreads*nNode, EXEC_lmp, script, OUT_PATH, '${MEAM_library_DIR}', SCRPT_DIR, var)
		elif execc == 'py':
			print >> someFile, "python3 %s %s\n"%(script, var)
		elif execc == 'kmc':
#			print >> someFile, "time mpiexec %s %s\n"%(script, var)
			print >> someFile, "./%s %s\n"%(script,var)
			
	someFile.close()										  


if __name__ == '__main__':
    import os
    import numpy as np

    nruns	 = range(3)
    #
    nThreads = 1
    nNode	 = 1
    #
    jobname  = {
                0:'cracks', #'hydrogenFree',
               }[0]
    sourcePath = os.getcwd() +\
                {	
                    0:'/junk',
                    1:'/../postprocess/NiCoCrNatom1K',
                }[ 0 ] #--- must be different than sourcePath. set it to 'junk' if no path
        #
    sourceFiles = { 0:False,
                    1:['data_init.txt','data_minimized.txt'],
                 }[0] #--- to be copied from the above directory. set it to '0' if no file
    #
    EXEC_DIR = {0:'~/Project/git/lammps2nd/lammps/src', #--- path for executable file
                1:'~/Project/opt/deepmd-kit/bin' #--- path for executable file: deep potential
                }[0]
    #
    MEAM_library_DIR='/home/kamran.karimi1/Project/git/lammps2nd/lammps/potentials'
    #
    SCRPT_DIR = os.getcwd()+'/matlab' 
    #
    SCRATCH = None
    OUT_PATH = '.'
    if SCRATCH:
        OUT_PATH = '/scratch/${SLURM_JOB_ID}'
    #--- py script must have a key of type str!
    LmpScript = {   0:'in.PrepTemp0',
                    1.0:'matlab.sh', #--- bash script
                } 
    #
    def SetVariables():
        Variable = {
                0:' -var natoms 100000 -var cutoff 3.52 -var ParseData 0 -var ntype 3 -var DumpFile dumpInit.xyz -var WriteData data_init.txt',
                 1.0:' %s'%SCRPT_DIR,
                } 
        return Variable
    #--- different scripts in a pipeline
    indices = {
                0:[1.0], #--- minimize, add H, minimize,kart input, kart.sh to bash shell ,invoke kart
              }[ 0 ]
    Pipeline = list(map(lambda x:LmpScript[x],indices))
#	Variables = list(map(lambda x:Variable[x], indices))
    EXEC = list(map(lambda x:np.array(['lmp','py','kmc'])[[ type(x) == type(0), type(x) == type(''), type(x) == type(1.0) ]][0], indices))	
#        print('EXEC=',EXEC)
    #
    EXEC_lmp = ['lmp_mpi','lmp_serial','_lmp'][0]
    durtn = ['23:59:59','00:59:59','167:59:59'][ 2 ]
    mem = '8gb'
    partition = ['gpu-v100','parallel','cpu2019','single'][3]
    #--
    DeleteExistingFolder = True
    if DeleteExistingFolder:
        print('rm %s'%jobname)
        os.system( 'rm -rf %s;mkdir -p %s' % (jobname,jobname) ) #--- rm existing
    os.system( 'rm jobID.txt' )
    # --- loop for submitting multiple jobs
    path=os.getcwd() + '/%s' % ( jobname)
    os.system( 'ln -s %s/%s %s' % ( EXEC_DIR, EXEC_lmp, path ) ) # --- create folder & mv oar script & cp executable
    for irun in nruns:
        counter = irun
        Variable = SetVariables()
        Variables = list(map(lambda x:Variable[x], indices))
        writPath = os.getcwd() + '/%s/Run%s' % ( jobname, irun ) # --- curr. dir
        print ' create %s' % writPath
        os.system( 'mkdir -p %s' % ( writPath ) ) # --- create folder
        #---
        for script,indx in zip(Pipeline,range(100)):
#			os.system( 'cp %s/%s %s/lmpScript%s.txt' %( SCRPT_DIR, script, writPath, indx) ) #--- lammps script: periodic x, pxx, vy, load
            os.system( 'ln -s %s/%s %s' %( SCRPT_DIR, script, writPath) ) #--- lammps script: periodic x, pxx, vy, load
        if sourceFiles: 
            for sf in sourceFiles:
                os.system( 'cp %s/Run%s/%s %s' %(sourcePath, irun, sf, writPath) ) #--- lammps script: periodic x, pxx, vy, load
        #---
        makeOAR( path, 1, nThreads, durtn) # --- make oar script
        os.system( 'chmod +x oarScript.sh; mv oarScript.sh %s' % ( writPath) ) # --- create folder & mv oar scrip & cp executable
        jobname0 = jobname.split('/')[0] #--- remove slash
        os.system( 'sbatch --partition=%s --mem=%s --time=%s --job-name %s.%s --output %s.%s.out --error %s.%s.err \
                        --chdir %s -c %s -n %s %s/oarScript.sh >> jobID.txt'\
                       % ( partition, mem, durtn, jobname0, counter, jobname0, counter, jobname0, counter \
                           , writPath, nThreads, nNode, writPath ) ) # --- runs oarScript.sh! 
#			counter += 1


    os.system( 'mv jobID.txt %s' % ( os.getcwd() + '/%s' % ( jobname ) ) )